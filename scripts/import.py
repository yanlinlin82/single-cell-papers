import os
import sys
import re
import gzip
import json
import django
from datetime import datetime

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from core.models import Paper
from core.paper import parse_date

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: import.py <output-dir>')
        sys.exit(1)

    output_dir = sys.argv[1]
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if not re.match(r'.*\.2-info.json.gz$', file):
                continue

            source = root.rstrip('/').split('/')[-1]
            print(f"root: {root}, source: {source}")
            pmid = file.split('.')[0]

            info_file = os.path.join(root, file)
            answer_file = os.path.join(root, f'{pmid}.4-chat-answer.json.gz')
            if not os.path.exists(answer_file):
                print(f"Skipped because answer file not found: {answer_file}")
                continue

            print(f"importing {source} {pmid} ('{info_file}', '{answer_file}') ...")

            create_new = False
            any_changed = False
            paper_list = Paper.objects.filter(pmid=pmid)
            if paper_list:
                paper = paper_list[0]
                print(f"  paper.source: {paper.source}, source: {source}")
                if paper.source is not None and source < paper.source:
                    print("  skipped because not latest source")
                    continue
                if paper.source != source:
                    paper.source = source
                    any_changed = True
            else:
                paper = Paper(pmid=pmid, source=source)
                create_new = True
                any_changed = True

            with gzip.open(info_file, 'rt') as f:
                data = json.load(f)
                #print(json.dumps(data, indent=4))
                if data['pmid'] != pmid:
                    print(f"Skipped because pmid mismatch: {data['pmid']} != {pmid}")
                    continue
                if paper.title != data['title']:
                    paper.title = data['title']
                    any_changed = True
                if paper.journal != data['journal']:
                    paper.journal = data['journal']
                    any_changed = True
                if paper.pub_date != data['pub_date']:
                    paper.pub_date = data['pub_date']
                    any_changed = True
                if 'pub_date_dt' not in data:
                    data['pub_date_dt'] = parse_date(data['pub_date'])
                if paper.pub_date_dt != data['pub_date_dt']:
                    paper.pub_date_dt = data['pub_date_dt']
                    any_changed = True
                if paper.pub_year != data['pub_year']:
                    paper.pub_year = data['pub_year']
                    any_changed = True
                if paper.doi != data['doi']:
                    paper.doi = data['doi']
                    any_changed = True

            with gzip.open(answer_file, 'rt') as f:
                try:
                    data = json.load(f)
                    if 'content' not in data:
                        print(f"Skipped because 'content' not found: {answer_file}")
                        continue
                    if isinstance(data['content'], str):
                        data['content'] = json.loads(data['content'])
                except json.decoder.JSONDecodeError:
                    print(f"Skipped because JSONDecodeError: {answer_file}")
                    continue
                #print(json.dumps(data, indent=4))
                content = data['content']
                if paper.article_type != content['article_type']:
                    paper.article_type = content['article_type']
                    any_changed = True
                if paper.description != content['description']:
                    paper.description = content['description']
                    any_changed = True
                if paper.novelty != content['novelty']:
                    paper.novelty = content['novelty']
                    any_changed = True
                if paper.limitation != content['limitation']:
                    paper.limitation = content['limitation']
                    any_changed = True
                if paper.research_goal != content['research_goal']:
                    paper.research_goal = content['research_goal']
                    any_changed = True
                if paper.research_objects != content['research_objects']:
                    paper.research_objects = content['research_objects']
                    any_changed = True
                if paper.field_category != content['field_category']:
                    paper.field_category = content['field_category']
                    any_changed = True
                if paper.disease_category != content['disease_category']:
                    paper.disease_category = content['disease_category']
                    any_changed = True
                if paper.technique != content['technique']:
                    paper.technique = content['technique']
                    any_changed = True
                if paper.model_type != content['model_type']:
                    paper.model_type = content['model_type']
                    any_changed = True
                if paper.data_type != content['data_type']:
                    paper.data_type = content['data_type']
                    any_changed = True
                if paper.sample_size != content['sample_size']:
                    paper.sample_size = content['sample_size']
                    any_changed = True

            if any_changed:
                if create_new:
                    print(f"  create new paper: {paper}")
                else:
                    print(f"  update existed paper: {paper}")
                paper.save()
