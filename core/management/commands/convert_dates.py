from django.core.management.base import BaseCommand
from core.models import Paper
from core.paper import parse_date

class Command(BaseCommand):
    help = 'Convert pub_date to pub_date_dt'

    def handle(self, *args, **options):
        for paper in Paper.objects.all():
            raw_date = paper.pub_date
            parsed_date = parse_date(raw_date)
            if parsed_date:
                paper.pub_date_dt = parsed_date
                paper.save()
                self.stdout.write(self.style.SUCCESS(f'Successfully updated paper {paper.id}: {raw_date} -> {parsed_date}'))
            else:
                self.stdout.write(self.style.ERROR(f'Failed to parse date for paper {paper.id}: {raw_date}'))
