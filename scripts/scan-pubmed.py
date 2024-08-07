import os
import sys
import re
from lxml import etree
import gzip
import openai
import dotenv
import json
import httpx
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from core.models import Paper
from core.paper import parse_date

class PubmedArticle:
    def __init__(self, xml_node):
        self.xml_node = xml_node
        self._doi = None
        self._pmid = None
        self._title = None
        self._journal = None
        self._pub_date = None
        self._pub_year = None
        self._abstract = None

    @property
    def doi(self):
        if self._doi is None:
            self._doi = (self.xml_node.xpath('MedlineCitation/Article/ELocationID[@EIdType="doi"]/text()') or [None])[0]
            if self._doi is not None:
                self._doi = self._doi.rstrip('.')
        if self._doi is None:
            self._doi = (self.xml_node.xpath('PubmedData/ArticleIdList/ArticleId[@IdType="doi"]/text()') or [None])[0]
            if self._doi is not None:
                self._doi = self._doi.rstrip('.')
        return self._doi

    @property
    def pmid(self):
        if self._pmid is None:
            self._pmid = (self.xml_node.xpath('MedlineCitation/PMID/text()') or [None])[0]
            if self._pmid is None:
                self._pmid = (self.xml_node.xpath('PubmedData/ArticleIdList/ArticleId[@IdType="pubmed"]/text()') or [None])[0]
        return self._pmid

    @property
    def title(self):
        if self._title is None:
            text = []
            for node in self.xml_node.xpath('MedlineCitation/Article/ArticleTitle'):
                for child in node.itertext(with_tail=True):
                    if isinstance(child, etree._Element):
                        text.append(etree.tostring(child, encoding='unicode', method='html'))
                    else:
                        text.append(child)
            self._title = ''.join(text).rstrip('.')
        return self._title

    @property
    def journal(self):
        if self._journal is None:
            if self.xml_node is not None:
                self._journal = (self.xml_node.xpath('MedlineCitation/Article/Journal/Title/text()') or [None])[0]
        return self._journal

    @property
    def pub_date(self):
        self._parse_date()
        return self._pub_date
    
    @property
    def pub_year(self):
        self._parse_date()
        return self._pub_year

    @property
    def abstract(self):
        if self._abstract is None:
            abstract = ''
            for node in self.xml_node.xpath('MedlineCitation/Article/Abstract'):
                text_nodes = node.xpath('AbstractText[not(@Label)]/text()')
                if len(text_nodes) > 0:
                    abstract += ''.join(text_nodes)
                else:
                    section_text = []
                    for section in node.xpath('AbstractText[@Label]'):
                        text = []
                        text.append(section.get('Label') + ': ')
                        for child in section.itertext(with_tail=True):
                            if isinstance(child, etree._Element):
                                text.append(etree.tostring(child, encoding='unicode', method='html'))
                            else:
                                text.append(child)
                        section_text.append(''.join(text))
                    abstract += '\n'.join(section_text)
            self._abstract = abstract
        return self._abstract

    def _parse_date(self):
        if self._pub_date is None:
            if self.xml_node is not None:
                node = self.xml_node.xpath('MedlineCitation/Article/Journal/JournalIssue/PubDate')
                if len(node) == 0:
                    node = self.xml_node.xpath('MedlineCitation/Article/ArticleDate')

                if len(node) == 0:
                    self._pub_date = ''
                else:
                    node = node[0]
                    # eg. <PubDate><Year>2012</Year><Month>Jan</Month><Day>01</Day></PubDate>
                    #     <PubDate><Year>2012</Year><Month>Jan-Feb</Month></PubDate>
                    #     <PubDate><MedlineDate>2012 Jan-Feb</MedlineDate></PubDate>
                    year = node.xpath('Year/text()')
                    month = node.xpath('Month/text()')
                    day = node.xpath('Day/text()')
                    if len(year) == 0:
                        node = node.xpath('MedlineDate/text()')
                        if node is None:
                            self._pub_date = ''
                        else:
                            # eg. <MedlineDate>2012 Jan-Feb</MedlineDate> or <MedlineDate>2012</MedlineDate>
                            self._pub_date = node[0]
                    else:
                        self._pub_date = year[0]
                        if len(month) > 0:
                            self._pub_date += '-' + month[0]
                            if len(day) > 0:
                                self._pub_date += '-' + day[0]
        if self._pub_year is None:
            if self._pub_date:
                self._pub_year = parse_date(self._pub_date).year

    def __str__(self):
        return f"{self.pmid} - {self.pub_year} - {self.journal}\nTitle: {self.title}\nAbstract: {self.abstract}"

def article_match(article, keyword_list):
    for keyword in keyword_list:
        pattern = r'\b{}\b'.format(re.escape(keyword))
        if re.search(pattern, article.title, re.IGNORECASE) \
            or re.search(pattern, article.abstract, re.IGNORECASE):
            return True
    return False

def prepare_gpt_in_msg(title, abstract):
    return [
        {
            "role": "system",
            "content": """
You are an information extracting bot. You extracts key information of one scientific paper from provided title and abstract, and translate them into Chinese.

The extracted key information should be output in JSON format as:

{
  "article_type": "...",
  "description": "...",
  "novelty": "...",
  "limitation": "...",
  "research_goal": "...",
  "research_objects": "...",
  "field_category": "...",
  "disease_category": "...",
  "technique": "...",
  "model_type": "...",
  "data_type": "...",
  "sample_size": "...",
}

Some cretirea for the key information:

- article_type: pick one of the values of research paper, review, meta-analysis, comments, correction, ...
- description: Use a short sentence to describe the main content of the article.
- novelty: Explain the innovation points of this article.
- limitation: Explain the limitations of this article.
- research_goal: Briefly explain the research purpose or field of this article.
- research_objects: Briefly explain the research objects of this article.
- field_category: pick one of the values of computer vision, natural language processing, machine learning, digital pathology, ...,
- disease_category: pick one of the values of lung cancer, prostate cancer, cardiovascular disease, geriatric disease, ...,
- technique: what kind of technique is used in this paper, e.g. NGS, ONT, RNA-seq, methylation sequencing, ...
- model_type: which model is used in this paper, e.g. CNN, LSTM, GAN, ...
- data_type: what kind of data is used in this paper, e.g. image, text, video, ...,
- sample_size: how many (and what kind of) samples has been involved in this research,
- If no any supported information in the title and abstract, output "NA" for the corresponding key.
- All values should be translated into Chinese, unless some abbr. that are clear enough to keep in English.
- Sentences should not have a period at the end.
"""
        },
        {
            "role": "user",
            "content": f"""
Here goes the paper title and abstract:

Title: {title}

Abstract: {abstract}
"""
        },
    ]

def prepare_gpt_input(title, abstract, gpt_input_file):
    if os.path.exists(gpt_input_file):
        with gzip.open(gpt_input_file, 'rt', encoding='utf-8') as gz_file:
            return json.load(gz_file)
    else:
        in_msg = prepare_gpt_in_msg(title, abstract)
        with gzip.open(gpt_input_file, 'wt', encoding='utf-8') as gz_file:
            json_str = json.dumps(in_msg, ensure_ascii=False, indent=4)
            gz_file.write(json_str)
        return in_msg

def fix_invalid_json_str(json_str):
    content = json_str.strip()
    if re.match('```json', content):
        content = re.sub(r'^```json', '', content, flags=re.MULTILINE)
        content = re.sub(r'```$', '', content, flags=re.MULTILINE)
        content = content.strip()
    content = re.sub(r',\s*}', '}', content) # remove trailing comma before '}'
    return content

def ask_gpt(pmid, title, abstract, input_file, output_file):
    print(f"Asking GPT for {pmid} ...")
    in_msg = prepare_gpt_input(title, abstract, input_file)
    out_msg = None
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key is None:
            print("ERROR: OPENAI_API_KEY not set!")
            return None
        client = openai.OpenAI(api_key=api_key)

        base_url = os.environ.get("OPENAI_BASE_URL")
        if base_url is not None:
            client.base_url = base_url

        proxy_url = os.environ.get("OPENAI_PROXY_URL")
        if proxy_url is None or proxy_url == "":
            client.http_client = httpx.Client(proxy=proxy_url)

        model = os.environ.get("OPENAI_MODEL")
        if model is None:
            print("ERROR: OPENAI_MODEL not set!")
            return None

        completion = client.chat.completions.create(
            model = model,
            messages = in_msg,
        )
        out_msg = completion.choices[0].message
    except Exception as e:
        print("ERROR: Failed to connect to OpenAI server! " + str(e))
        return None
    
    if out_msg is None or not hasattr(out_msg, 'role') or not hasattr(out_msg, 'content'):
        print("ERROR: Invalid response from OpenAI server!")
        return None

    data = {
        "role": out_msg.role,
        "content": "",
    }
    content = fix_invalid_json_str(out_msg.content)
    try:
        data['content'] = json.loads(content)
    except Exception as e:
        data['content'] = out_msg.content # keep original content
        print(f"ERROR: Failed to parse JSON content: {e}")

    with gzip.open(output_file, 'wt', encoding='utf-8') as gz_file:
        json_str = json.dumps(data, ensure_ascii=False, indent=4)
        gz_file.write(json_str)
    return data['content']

def update_ai_parsed_results(paper, data):
    any_updated = False
    if paper.article_type != data.get('article_type', ''):
        paper.article_type = data.get('article_type', '')
        any_updated = True
    if paper.description != data.get('description', ''):
        paper.description = data.get('description', '')
        any_updated = True
    if paper.novelty != data.get('novelty', ''):
        paper.novelty = data.get('novelty', '')
        any_updated = True
    if paper.limitation != data.get('limitation', ''):
        paper.limitation = data.get('limitation', '')
        any_updated = True
    if paper.research_goal != data.get('research_goal', ''):
        paper.research_goal = data.get('research_goal', '')
        any_updated = True
    if paper.research_objects != data.get('research_objects', ''):
        paper.research_objects = data.get('research_objects', '')
        any_updated = True
    if paper.field_category != data.get('field_category', ''):
        paper.field_category = data.get('field_category', '')
        any_updated = True
    if paper.disease_category != data.get('disease_category', ''):
        paper.disease_category = data.get('disease_category', '')
        any_updated = True
    if paper.technique != data.get('technique', ''):
        paper.technique = data.get('technique', '')
        any_updated = True
    if paper.model_type != data.get('model_type', ''):
        paper.model_type = data.get('model_type', '')
        any_updated = True
    if paper.data_type != data.get('data_type', ''):
        paper.data_type = data.get('data_type', '')
        any_updated = True
    if paper.sample_size != data.get('sample_size', ''):
        paper.sample_size = data.get('sample_size', '')
        any_updated = True
    return any_updated

def write_pubmed_xml_file(xml_node, pubmed_xml_file):
    if not os.path.exists(pubmed_xml_file):
        with gzip.open(pubmed_xml_file, 'wt', encoding='utf-8') as gz_file:
            xml_str = etree.tostring(xml_node, encoding='utf-8').decode('utf-8')
            gz_file.write(xml_str)

def parse_pubmed_xml(article):
    try:
        data = {
            "doi": article.doi,
            "pmid": article.pmid,
            "title": article.title,
            "journal": article.journal,
            "pub_date": article.pub_date,
            "pub_year": article.pub_year,
            "abstract": article.abstract,
        }
        return data
    except Exception as e:
        print(f"  failed to extract data for {article.pmid}: " + str(e))
        raise

def write_pubmed_json_file(data, pubmed_json_file):
    if not os.path.exists(pubmed_json_file):
        with gzip.open(pubmed_json_file, 'wt', encoding='utf-8') as gz_file:
            json_str = json.dumps(data, ensure_ascii=False, indent=4)
            gz_file.write(json_str)

def parse_by_ai(title_or_abstract_changed, pmid, title, abstract, paper, data, output_dir):
    if title is None or title == "":
        print(f"  Skip asking GPT for {pmid}, no title ...")
        return False

    if paper.abstract is None or paper.abstract == "":
        print(f"  Skip asking GPT for {pmid}, no abstract ...")
        return False

    ai_ask_file = os.path.join(output_dir, f"{pmid}.3-chat-ask.json.gz")
    ai_answer_file = os.path.join(output_dir, f"{pmid}.4-chat-answer.json.gz")
    if not os.path.exists(ai_answer_file) or title_or_abstract_changed:
        res = ask_gpt(pmid, title, abstract, ai_ask_file, ai_answer_file)
    else:
        with gzip.open(ai_answer_file, 'rt', encoding='utf-8') as gz_file:
            res = json.load(gz_file).get('content', None)

    if res is None:
        print(f"  Skip asking GPT for {pmid}, no response ...")
        return False
    elif isinstance(res, str):
        try:
            print(f"  Fixing invalid JSON string ...")
            print(f"  before: {res}")
            res = fix_invalid_json_str(res)
            print(f"  after: {res}")
            res = json.loads(res)
        except Exception as e:
            print(f"  Skip asking GPT for {pmid}, failed to parse response: {e}")
            print(f"  res = {res}")
            return False
    elif not isinstance(res, dict):
        print(f"  Skip asking GPT for {pmid}, invalid response ...")
        print(f"  res = {res}")
        return False
    else:
        pass

    data.update(res)
    any_updated = update_ai_parsed_results(paper, res)
    if any_updated:
        paper.parse_time = django.utils.timezone.now()
    return any_updated

def process_single(xml_source_id, article, output_dir):

    write_pubmed_xml_file(article.xml_node, os.path.join(output_dir, f"{article.pmid}.1-pubmed.xml.gz"))
    data = parse_pubmed_xml(article)
    write_pubmed_json_file(data, os.path.join(output_dir, f"{article.pmid}.2-info.json.gz"))

    create_new = False
    any_updated = False
    need_parse_by_ai = False  # only parse by AI if title or abstract changed
    paper_list = Paper.objects.filter(pmid=article.pmid)
    if paper_list:
        paper = paper_list[0]
        if paper.source is not None and xml_source_id < paper.source:
            print(f"  skipped because not latest source (xml:{xml_source_id}) < (db:{paper.source})")
            return False, False, False

        if paper.source is None or paper.source != xml_source_id:
            paper.source = xml_source_id
            any_updated = True
    else:
        paper = Paper(pmid=article.pmid, source=xml_source_id)
        create_new = True
        any_updated = True

    title_or_abstract_changed = False
    if create_new or (paper.title != data['title'] or paper.abstract != data['abstract']):
        title_or_abstract_changed = True

    if paper.title != data['title']:
        paper.title = data['title']
        any_updated = True
    if paper.journal != data['journal']:
        paper.journal = data['journal']
        any_updated = True
    if paper.pub_date != data['pub_date']:
        paper.pub_date = data['pub_date']
        any_updated = True
    pub_date_dt = parse_date(data['pub_date'])
    if paper.pub_date_dt != pub_date_dt:
        paper.pub_date_dt = pub_date_dt
        any_updated = True
    if paper.pub_year != data['pub_year']:
        paper.pub_year = data['pub_year']
        any_updated = True
    if paper.doi != data['doi']:
        paper.doi = data['doi']
        any_updated = True
    if paper.abstract != data['abstract']:
        paper.abstract = data['abstract']
        any_updated = True

    if parse_by_ai(title_or_abstract_changed, article.pmid, article.title, article.abstract, paper, data, output_dir):
        any_updated = True

    if any_updated:
        paper.save()

    print("====================================")
    print(json.dumps(data, ensure_ascii=False, indent=4))

    return create_new, not create_new, need_parse_by_ai

def process(xml_gz_file, keyword_list):
    xml_source_id = os.path.basename(xml_gz_file).split('.')[0]
    output_dir = os.path.join('output', xml_source_id)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    cnt, new_cnt, updated_cnt, ai_updated_cnt = 0, 0, 0, 0
    tree = etree.parse(xml_gz_file)
    root = tree.getroot()
    total = len(root.xpath('/PubmedArticleSet/PubmedArticle'))
    for index, xml_node in enumerate(root.xpath('/PubmedArticleSet/PubmedArticle')):
        article = PubmedArticle(xml_node)
        if not article_match(article, keyword_list):
            continue

        cnt += 1
        print(f"Processing ({xml_source_id} - {index + 1}/{total} - {cnt}): (PMID: {article.pmid}) {article.title}")

        created, updated, ai_updated = process_single(xml_source_id, article, output_dir)
        if created:
            new_cnt += 1
        if updated:
            updated_cnt += 1
        if ai_updated:
            ai_updated_cnt += 1

    print(f"Processing {xml_gz_file} completed!")
    print(f"Total articles: {index + 1}, matched articles: {cnt} ({new_cnt} new, {updated_cnt} updated, {ai_updated_cnt} AI updated)")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <pubmed.xml.gz>")
        sys.exit(1)

    print(f"Processing {sys.argv[1]} ...")
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if not os.path.exists(env_file):
        print(f"ERROR: Environment file {env_file} not found!")
        sys.exit(1)
    print(f"Loading environment variables from {env_file}")
    dotenv.load_dotenv(env_file)

    process(sys.argv[1], [
        'single-cell sequencing',
        'single-cell RNA sequencing',
        'single-cell transcriptomics',
        'single-cell RNA-seq',
        'single-cell transcriptome',
        'scRNA-seq',
        'spatial transcriptomics'
        ])
