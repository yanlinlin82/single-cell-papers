import os
import sys
import django
import re
import gzip
import json

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from core.models import Paper

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: import.py <output-dir>')
        sys.exit(1)

    output_dir = sys.argv[1]
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if not re.match(r'.*\.2-info.json.gz$', file):
                continue
            info_file = os.path.join(root, file)
            answer_file = os.path.join(root, f'{file.split(".")[0]}.4-chat-answer.json.gz')
            if not os.path.exists(answer_file):
                print(f"Skipped because answer file not found: {answer_file}")
                continue

            pmid = file.split('.')[0]

            print(f"importing {pmid} ('{info_file}', '{answer_file}') ...")
            #print("====================================")
            #print(f"pmid: {pmid}")

            paper_list = Paper.objects.filter(pmid=pmid)
            if paper_list:
                paper = paper_list[0]
                print(f"  update existed paper: {paper}")
            else:
                paper = Paper(pmid=pmid)
                print(f"  add new paper: {pmid}")

            with gzip.open(info_file, 'rt') as f:
                data = json.load(f)
                #print(json.dumps(data, indent=4))
                if data['pmid'] != pmid:
                    print(f"Skipped because pmid mismatch: {data['pmid']} != {pmid}")
                    continue
                paper.title = data['title']
                paper.journal = data['journal']
                paper.pub_date = data['pub_date']
                paper.pub_year = data['pub_year']
                paper.doi = data['doi']
            
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
                paper.article_type = data['content']['article_type']
                paper.description = data['content']['description']
                paper.novelty = data['content']['novelty']
                paper.limitation = data['content']['limitation']
                paper.research_goal = data['content']['research_goal']
                paper.research_objects = data['content']['research_objects']
                paper.field_category = data['content']['field_category']
                paper.disease_category = data['content']['disease_category']
                paper.technique = data['content']['technique']
                paper.model_type = data['content']['model_type']
                paper.data_type = data['content']['data_type']
                paper.sample_size = data['content']['sample_size']

            paper.save()
