import os
import sys
import datetime
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

def ask_gpt(title, abstract, output_dir, pmid):
    if abstract is None or abstract == "":
        print(f"  Skip asking GPT for {pmid}, no abstract ...")
        return None

    if os.path.exists(os.path.join(output_dir, f"{pmid}.4-chat-answer.json.gz")):
        print(f"  Skip asking GPT for {pmid}, load from cache ...")
        with gzip.open(os.path.join(output_dir, f"{pmid}.4-chat-answer.json.gz"), 'rt', encoding='utf-8') as gz_file:
            data = json.load(gz_file)
            return data.get('content')

    print(f"Asking GPT for {pmid} ...")
    in_msg = [
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

    with gzip.open(os.path.join(output_dir, f"{pmid}.3-chat-ask.json.gz"), 'wt', encoding='utf-8') as gz_file:
        json_str = json.dumps(in_msg, ensure_ascii=False, indent=4)
        gz_file.write(json_str)

    out_msg = None
    try:
        proxy_url = os.environ.get("OPENAI_PROXY_URL")
        if proxy_url is None or proxy_url == "":
            client = openai.OpenAI()
        else:
            client = openai.OpenAI(http_client=httpx.Client(proxy=proxy_url))
        completion = client.chat.completions.create(
            model = os.environ.get("OPENAI_MODEL"),
            messages = in_msg,
        )
        out_msg = completion.choices[0].message
    except Exception as e:
        print("Failed to connect to OpenAI server! " + str(e))
    
    if out_msg is not None:
        data = {
            "role": out_msg.role,
            "content": "",
        }
        try:
            data['content'] = json.loads(out_msg.content)
        except Exception as e:
            data['content'] = out_msg.content

        with gzip.open(os.path.join(output_dir, f"{pmid}.4-chat-answer.json.gz"), 'wt', encoding='utf-8') as gz_file:
            json_str = json.dumps(data, ensure_ascii=False, indent=4)
            gz_file.write(json_str)
        return data['content']

    return None

def process(xml_gz_file):
    xml_source_id = os.path.basename(xml_gz_file).split('.')[0]
    output_dir = os.path.join('output', xml_source_id)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    cnt = 0
    tree = etree.parse(xml_gz_file)
    root = tree.getroot()
    for index, xml_node in enumerate(root.xpath('/PubmedArticleSet/PubmedArticle')):
        article = PubmedArticle(xml_node)
        if article_match(article, [
            'single-cell sequencing',
            'single-cell RNA sequencing',
            'single-cell transcriptomics',
            'single-cell RNA-seq',
            'single-cell transcriptome',
            'scRNA-seq',
            'spatial transcriptomics'
            ]):
            cnt += 1
            print(f"Processing ({cnt}): (PMID: {article.pmid}) {article.title}")

            paper = Paper.objects.filter(pmid=article.pmid)
            if paper:
                if paper[0].source is not None and xml_source_id < paper[0].source:
                    print("  skipped because not latest source")
                    continue

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
            except Exception as e:
                print(f"  failed to extract data for {article.pmid}: " + str(e))
                raise

            with gzip.open(os.path.join(output_dir, f"{article.pmid}.1-pubmed.xml.gz"), 'wt', encoding='utf-8') as gz_file:
                xml_str = etree.tostring(article.xml_node, encoding='utf-8').decode('utf-8')
                gz_file.write(xml_str)

            with gzip.open(os.path.join(output_dir, f"{article.pmid}.2-info.json.gz"), 'wt', encoding='utf-8') as gz_file:
                json_str = json.dumps(data, ensure_ascii=False, indent=4)
                gz_file.write(json_str)

            res = ask_gpt(article.title, article.abstract, output_dir, article.pmid)
            if res is not None and isinstance(res, dict):
                data.update(res)

            print("====================================")
            print(json.dumps(data, ensure_ascii=False, indent=4))

    print(f"Processing {xml_gz_file} completed!")
    print(f"Total articles: {index + 1}, matched articles: {cnt}")

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

    process(sys.argv[1])
