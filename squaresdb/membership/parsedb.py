#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import argparse
import csv
import os
import re
import sys

if __name__ == '__main__':
    CUR_FILE = os.path.abspath(__file__)
    DJANGO_DIR = os.path.abspath(os.path.join(os.path.dirname(CUR_FILE), '..', '..'))
    sys.path.append(DJANGO_DIR)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'squaresdb.settings'

#pylint:disable=wrong-import-position

import django
django.setup()
from django.core import management
from django.db import transaction
from django.contrib.auth.models import User

import reversion as revisions

import squaresdb.membership.models

# Format:
# %A Name
# %D Class (from docs: date this item updated)
# %N Email
# %K Frequency
# %T Town
# %P Zip code
# %L Street address
# %S State
# %H Phone number (home?)
# %O MIT affiliation (alum/staff/student) (from docs: other comments)
# %W Phone number (work?)
# %E comments (pronunciation, maiden name, parents phone number, etc.) -- docs mention employer
# %J Reason for removing from signin?
# %Q name for mailings (eg, "John and Jane Doe")
# %U reason no longer receives mailing (commonly, combined with spouse)
# %M Campus mailing address (in a few cases, indicated doesn't want to give
# address and %U is set too)
# %I prepaid subscription ("subscription" or number of weeks)
# %C Country (or "Cambridge"...)
# %V Additional address line (mostly FSILG, but some others)
# %B PO Box (1 case)

FIELDS = (
    ('#', 'row'),
    ('A', 'name'),
    ('d', 'class'),
    ('D', 'last_update_info'),
    ('N', 'email'),
    ('O', 'mitaffil'),
    ('E', 'comments'),
    ('J', 'no_signin_reason'),
    ('U', 'no_mail_reason'),
    # address info
    ('Q', 'mail_name'),
    ('M', 'campus_addr'),
    ('B', 'pobox'),
    ('L', 'street'),
    ('V', 'addr2'),
    ('T', 'town'),
    ('P', 'zip'),
    ('S', 'state'),
    ('C', 'country'),
    # ignored fields
    ('K', 'frequency'),
    ('I', 'subscription'),
    ('H', 'home'),
    ('W', 'work'),
)
CODES = dict(FIELDS)
LABELS = [l for k, l in FIELDS]

CLASS_RE = re.compile(r"(?P<class>(spring|fall) \d+ (?P<pe>PE |))class[ ,.;]*(?P<update>.*)", re.I)

def initial_dict(entry):
    return {'row':entry}

def _parse_line(line, names, data):
    code = line[1]
    label = CODES[code]
    _code_str, _space, rest = line.partition(' ')
    if code == 'A':
        names.append(rest)
    elif code == 'E':
        if label in data:
            data[label] += '\n' + rest
        else:
            data[label] = rest
    elif code == 'D':
        match = CLASS_RE.match(rest)
        if match:
            data['class'] = match.group('class')
            data[label] = match.group('update')
        else:
            data[label] = rest
    else:
        assert label not in data, "Non-unique line: data=%s, line='%s'" % (data, line)
        data[label] = rest

def parse_to_dicts(db_fp):
    entries = []

    is_first = True
    names = []
    entry = 1
    for line in db_fp:
        line = line.strip()
        if not line or is_first:
            if names:
                for name in names:
                    data = data.copy()
                    data['name'] = name
                    entries.append(data)
                entry += 1
            data = initial_dict(entry)
            names = []
            is_first = False
        elif line.startswith(r'.\"'):
            pass # comment line
        else:
            assert len(line) >= 2 and line[0] == '%', "unexpected line: %s" % (line, )
            _parse_line(line, names, data)

    return entries

def dump_dicts(csv_fp, entries):
    writer = csv.DictWriter(csv_fp, LABELS)
    writer.writeheader()
    writer.writerows(entries)

def parse_person_type(affil):
    if 'alum' in affil:
        return 'alum', 'full'
    elif affil in ('MIT undergrad', 'MIT student'):
        # fix "MIT Student" entries before final import
        return 'undergrad', 'mit-student'
    elif affil == 'MIT grad student':
        return 'grad', 'mit-student'
    elif affil == 'student':
        return 'none', 'student'
    elif affil == 'staff':
        return 'staff', 'full'
    else:
        assert affil == ''
        return 'none', 'full'

def load_row(row, system_people):
    person = squaresdb.membership.models.Person()
    person.name = row['name']
    person.email = row['email']
    person.level_id = '?'
    if row['class']:
        person.status_id = 'grad'
        tsclass, _created = squaresdb.membership.models.TSClass.objects.get_or_create(
            label=row['class'], defaults=dict(coordinator=system_people['cc'])
        )
    else:
        person.status_id = 'member'
        tsclass = None
    person.mit_affil_id, person.fee_cat_id = parse_person_type(row['mitaffil'])
    person.frequency_id = row['frequency'] or "never"
    person.save()
    if tsclass:
        TSClassMember = squaresdb.membership.models.TSClassMember
        TSClassMember.objects.create(student=person, clas=tsclass, pe=False)

    comments = []
    if row['comments']:
        comments.append("Comments: "+row['comments'])
    if row['last_update_info']:
        comments.append("Last update: "+row['last_update_info'])
    if row['no_signin_reason']:
        comments.append("No signin reason: "+row['no_signin_reason'])
    if row['no_mail_reason']:
        comments.append("No mail reason: "+row['no_mail_reason'])
    if comments:
        author = User.objects.get(username='importer@SYSTEM')
        comment = squaresdb.membership.models.PersonComment(author=author, person=person)
        comment.body = '\n\n'.join(comments)
        comment.save()

@transaction.atomic
@revisions.create_revision()
def load_csv(csv_fp):
    revisions.set_comment("Loading people from CSV file")
    importer = User.objects.get(username='importer@SYSTEM')
    revisions.set_user(importer)

    reader = csv.DictReader(csv_fp)
    Person = squaresdb.membership.models.Person
    system_people = dict(
        cc=Person.objects.get(email='squaresdb-placeholder-cc@mit.edu'),
    )
    for row in reader:
        load_row(row, system_people)

def parse_args():
    parser = argparse.ArgumentParser(description='parse legacy Tech Squares DB')
    parser.add_argument('mode', type=str, choices=('legacy2csv', 'csv2django'))
    parser.add_argument('--csv', type=str, required=True)
    parser.add_argument('--no-initial-revisions', action='store_false', dest='initial_revs')
    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    if args.mode == 'legacy2csv':
        parsed_db = parse_to_dicts(sys.stdin)
        with open(args.csv, 'w') as csv_fp:
            dump_dicts(csv_fp, parsed_db)
    else:
        assert args.mode == 'csv2django'
        if args.initial_revs:
            print("Creating initial revisions...")
            management.call_command('createinitialrevisions', 'membership',
                                    comment='Initial revision (pre-import)')
            print("Created initial revisions.")
        with open(args.csv, 'r') as csv_fp:
            print("Importing CSV file...")
            load_csv(csv_fp)

if __name__ == '__main__':
    main()
