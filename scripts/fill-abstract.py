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

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <output>")
        sys.exit(1)

    output_dir = sys.argv[1]
    for root, dirs, files in os.walk(output_dir):
        xml_source_id = root.split('/')[-1]
        print(f"Processing {xml_source_id}")

        for file in files:
            if not re.search(r'2-info.json.gz$', file):
                continue

            pmid = file.split('.')[0]
            print(f"{pmid} - {os.path.join(root, file)}")
            with gzip.open(os.path.join(root, file), 'rt') as f:
                info = json.load(f)
                if info['pmid'] != pmid:
                    print(f"PMID mismatch: {info['pmid']} != {pmid}")
                    continue
                if 'abstract' not in info or not info['abstract']:
                    print(f"No abstract found for {pmid}")
                    continue
                paper_list = Paper.objects.filter(pmid=pmid)
                if len(paper_list) == 0:
                    print(f"No paper found for {pmid}")
                    continue
                paper = paper_list[0]
                if xml_source_id < paper.source:
                    print(f"Skipping {pmid} - (json:{xml_source_id}) < (db:{paper.source})")
                    continue
                if paper.abstract != info['abstract']:
                    print(f"Updating abstract for {pmid}")
                    paper.abstract = info['abstract']
                    paper.save()
