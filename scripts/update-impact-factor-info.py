import os
import sys
import re
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from core.models import Journal, Paper

def match_journal(name):
    journal = Journal.objects.filter(name__iexact=name).first()
    if not journal:
        journal = Journal.objects.filter(abbreviation__iexact=name).first()
    return journal

cnt, updated = 0, 0
for paper in Paper.objects.all():
    cnt += 1

    journal_name = paper.journal.strip()
    journal_name = re.sub(r'\s+', ' ', journal_name)
    if not journal_name:
        continue

    journal = match_journal(journal_name)
    if not journal:
        journal_name_2 = re.sub(r'\s+:\s+.*$', '', journal_name)
        journal = match_journal(journal_name_2)
        if not journal:
            journal_name_3 = re.sub(r'the journal of', 'journal of', journal_name, flags=re.IGNORECASE)
            journal = match_journal(journal_name_3)

    if journal:
        paper.journal_abbreviation = journal.abbreviation
        paper.journal_impact_factor = journal.impact_factor
        paper.journal_impact_factor_quartile = journal.impact_factor_quartile
        paper.save()
        print(f"Updated: {paper}")
        updated += 1
    else:
        print(f"Journal '{paper.journal}' not found.")

print(f"Total {cnt} papers processed, {updated} papers updated.")
