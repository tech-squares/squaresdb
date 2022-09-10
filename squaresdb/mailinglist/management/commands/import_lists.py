import csv
import sys

from django.core.management.base import BaseCommand, CommandError

from ... import models as mail_models

# To update lists in SquaresDB:
# (1) Update the mailing lists spreadsheet
# (2) Run this script to load into DB
# (3) Update the fixture with something like:
# ../manage.py dumpdata --indent=2 mailinglist.{ListCategory,MailingList} \
# > mailinglist/fixtures/squares.json 

class Command(BaseCommand):
    help = 'Import lists from CSV'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        reader = csv.DictReader(sys.stdin)
        lists = []
        for row in reader:
            if row['category'] == 'skip':
                continue
            category = mail_models.ListCategory.objects.get(slug=row['category'])
            data = dict(list_type=row['list_type'], category=category,
                        order=row['order'], description=row['db_desc'])
            mlist, created = mail_models.MailingList.objects.get_or_create(name=row['name'],
                                                                           defaults=data)
            msg = f"Processed list {row['name']} ({created=}): {row=}"
            if created:
                msg = self.style.SUCCESS(msg)
            self.stdout.write(msg)
