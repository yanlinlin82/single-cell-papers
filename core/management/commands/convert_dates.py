import re
from datetime import datetime
from django.core.management.base import BaseCommand
from core.models import Paper

season_to_month = {
    "Spring": 3,
    "Summer": 6,
    "Autumn": 9,
    "Winter": 12
}

class Command(BaseCommand):
    help = 'Convert pub_date to pub_date_dt'

    def handle(self, *args, **options):
        for paper in Paper.objects.all():
            raw_date = paper.pub_date
            parsed_date = self.parse_date(raw_date)
            if parsed_date:
                paper.pub_date_dt = parsed_date
                paper.save()
                self.stdout.write(self.style.SUCCESS(f'Successfully updated paper {paper.id}: {raw_date} -> {parsed_date}'))
            else:
                self.stdout.write(self.style.ERROR(f'Failed to parse date for paper {paper.id}: {raw_date}'))

    def parse_date(self, raw_date):
        try:
            # Parse the date using multiple formats
            if re.match(r'\d{4}-[a-zA-Z]{3}-\d{2}', raw_date):
                # e.g. 2020-Jan-01
                return datetime.strptime(raw_date, '%Y-%b-%d').date()
            elif re.match(r'\d{4}-[a-zA-Z]{3}', raw_date):
                # e.g. 2020-Jan
                return datetime.strptime(raw_date, '%Y-%b').date().replace(day=1)
            elif re.match(r'\d{4}-\d{2}-\d{2}', raw_date):
                # e.g. 2020-01-01
                return datetime.strptime(raw_date, '%Y-%m-%d').date()
            elif re.match(r'\d{4}\s+[a-zA-Z]{3}-[a-zA-Z]{3}\s+\d{2}', raw_date):
                # e.g. 2023 Jan-Feb 01
                pattern = r'(\d{4})\s+([a-zA-Z]{3})-[a-zA-Z]{3}\s+(\d{2})'
                match = re.match(pattern, raw_date)
                year, month, day = match.groups()
                formatted_date_str = f"{year} {month} {day}"
                return datetime.strptime(formatted_date_str, '%Y %b %d').date()
            elif re.match(r'\d{4}\s+[a-zA-Z]{3}-[a-zA-Z]{3}', raw_date):
                # e.g. 2023 Jan-Feb
                pattern = r'(\d{4})\s+([a-zA-Z]{3})-[a-zA-Z]{3}'
                match = re.match(pattern, raw_date)
                year, month = match.groups()
                formatted_date_str = f"{year} {month}"
                return datetime.strptime(formatted_date_str, '%Y %b').date().replace(day=1)
            elif re.match(r'\d{4}-\d{2}', raw_date):
                # e.g. 2020-01
                return datetime.strptime(raw_date, '%Y-%m').date().replace(day=1)
            elif re.match(r'\d{4} (Spring|Summer|Autumn|Winter)', raw_date):
                # e.g. 2020 Spring
                year, season = raw_date.split(' ')
                month = season_to_month[season]
                return datetime.strptime(f"{year}-{month}-01", '%Y-%m-%d').date()
            elif re.match(r'\d{4}', raw_date):
                # e.g. 2020
                return datetime.strptime(raw_date, '%Y').date().replace(month=1, day=1)
            else:
                return None
        except ValueError:
            return None
