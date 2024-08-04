import re
from datetime import datetime

season_to_month = {
    "Spring": 3,
    "Summer": 6,
    "Autumn": 9,
    "Winter": 12
}

def parse_date(raw_text):
    try:
        # Parse the date using multiple formats
        if re.match(r'\d{4}-[a-zA-Z]{3}-\d{2}', raw_text):
            # e.g. 2020-Jan-01
            return datetime.strptime(raw_text, '%Y-%b-%d').date()
        elif re.match(r'\d{4}-[a-zA-Z]{3}', raw_text):
            # e.g. 2020-Jan
            return datetime.strptime(raw_text, '%Y-%b').date().replace(day=1)
        elif re.match(r'\d{4}-\d{2}-\d{2}', raw_text):
            # e.g. 2020-01-01
            return datetime.strptime(raw_text, '%Y-%m-%d').date()
        elif re.match(r'\d{4}\s+[a-zA-Z]{3}-[a-zA-Z]{3}\s+\d{2}', raw_text):
            # e.g. 2023 Jan-Feb 01
            pattern = r'(\d{4})\s+([a-zA-Z]{3})-[a-zA-Z]{3}\s+(\d{2})'
            match = re.match(pattern, raw_text)
            year, month, day = match.groups()
            formatted_date_str = f"{year} {month} {day}"
            return datetime.strptime(formatted_date_str, '%Y %b %d').date()
        elif re.match(r'\d{4}\s+[a-zA-Z]{3}-[a-zA-Z]{3}', raw_text):
            # e.g. 2023 Jan-Feb
            pattern = r'(\d{4})\s+([a-zA-Z]{3})-[a-zA-Z]{3}'
            match = re.match(pattern, raw_text)
            year, month = match.groups()
            formatted_date_str = f"{year} {month}"
            return datetime.strptime(formatted_date_str, '%Y %b').date().replace(day=1)
        elif re.match(r'\d{4}-\d{2}', raw_text):
            # e.g. 2020-01
            return datetime.strptime(raw_text, '%Y-%m').date().replace(day=1)
        elif re.match(r'\d{4} (Spring|Summer|Autumn|Winter)', raw_text):
            # e.g. 2020 Spring
            year, season = raw_text.split(' ')
            month = season_to_month[season]
            return datetime.strptime(f"{year}-{month}-01", '%Y-%m-%d').date()
        elif re.match(r'\d{4}', raw_text):
            # e.g. 2020
            return datetime.strptime(raw_text, '%Y').date().replace(month=1, day=1)
        else:
            return None
    except ValueError:
        return None
