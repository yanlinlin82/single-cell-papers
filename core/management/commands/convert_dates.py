import re
from datetime import datetime
from django.core.management.base import BaseCommand
from core.models import Paper

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
                return datetime.strptime(raw_date, '%Y-%b-%d').date()
            elif re.match(r'\d{4}-[a-zA-Z]{3}', raw_date):
                return datetime.strptime(raw_date, '%Y-%b').date().replace(day=1)
            elif re.match(r'\d{4}', raw_date):
                return datetime.strptime(raw_date, '%Y').date().replace(month=1, day=1)
            elif re.match(r'\d{4}-\d{2}-\d{2}', raw_date):
                return datetime.strptime(raw_date, '%Y-%m-%d').date()
            else:
                return None
        except ValueError:
            return None
