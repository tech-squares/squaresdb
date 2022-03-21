from collections import Counter
import datetime

from django.core.management.base import BaseCommand, CommandError
import reversion
from ... import models as mail_models

class Command(BaseCommand):
    help = 'Sync mailing list membership into DB'

    def add_arguments(self, parser):
        parser.add_argument('list', nargs='*', type=str)

    def handle_list(self, lst):
        msg = "%s: Syncing %s" % (datetime.datetime.now(), lst.name)
        self.stdout.write(self.style.SUCCESS(msg))
        new_members = set(lst.get_list().list_members())
        old_members = lst.listmember_set.all()
        count = Counter()
        to_add = []
        kept = set()
        for mem in old_members:
            if mem.email in new_members:
                kept.add(mem.email)
            else:
                count['delete'] += 1
                mem.delete()
        for mem in new_members:
            if mem not in kept:
                to_add.append(mail_models.ListMember(mail_list=lst, email=mem))
        mail_models.ListMember.objects.bulk_create(to_add)
        count['kept'] += len(kept)
        count['to_add'] += len(to_add)
        msg = "%s: Synced %s: %s" % (datetime.datetime.now(), lst.name, count)
        self.stdout.write(self.style.SUCCESS(msg))
        return count

    def handle(self, *args, **options):
        lists = mail_models.MailingList.objects.all()
        if options['list']:
            lists = lists.filter(name__in=options['list'])
            assert len(lists) == len(options['list'])

        total_count = Counter()
        for lst in lists:
            with reversion.create_revision(atomic=True):
                reversion.set_comment("cache_lists: list=" + lst.name)
                count = self.handle_list(lst)
            total_count += count

        msg = '%s: Processed %d lists: %s' % (datetime.datetime.now(),
                                                 len(lists), total_count)
        self.stdout.write(self.style.SUCCESS(msg))
