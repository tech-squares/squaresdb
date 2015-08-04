#!/usr/bin/env python

import argparse
import collections
import csv
import os
import re
import sys

if __name__ == '__main__':
    cur_file = os.path.abspath(__file__)
    django_dir = os.path.abspath(os.path.join(os.path.dirname(cur_file), '..', '..'))
    sys.path.append(django_dir)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'squaresdb.settings'

from django.db import transaction

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
# %M Campus mailing address (in a few cases, indicated doesn't want to give address and %U is set too)
# %I prepaid subscription ("subscription" or number of weeks)
# %C Country (or "Cambridge"...)
# %V Additional address line (mostly FSILG, but some others)
# %B PO Box (1 case)

fields = (
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
codes = {k: l for k,l in fields}
labels = [l for k,l in fields]

class_re = re.compile(r"(?P<class>(spring|fall) \d+ (?P<pe>PE |))class[ ,.;]*(?P<update>.*)", re.I)

def initial_dict(entry):
    return {'row':entry}

def parse_to_dicts(fp):
    entries = []

    code = False
    is_first = True
    entry = 1
    for line in fp:
        line = line.strip()
        if not line or is_first:
            if code:
                for name in names:
                    data = data.copy()
                    data['name'] = name
                    entries.append(data)
                entry += 1
            data = initial_dict(entry)
            names = []
            is_first = False
            code = False
        elif line.startswith(r'.\"'):
            pass # comment line
        else:
            assert len(line) >= 2 and line[0] == '%', "unexpected line: %s" % (line, )
            code = line[1]
            label = codes[code]
            code_str, space, rest = line.partition(' ')
            if code == 'A':
                names.append(rest)
            elif code == 'E':
                if label in data:
                    data[label] += '\n' + rest
                else:
                    data[label] = rest
            elif code == 'D':
                match = class_re.match(rest)
                if match:
                    #print "class=%s, pe=%s, rest=%s" % (match.group('class'), match.group('pe'), match.group('update'))
                    data['class'] = match.group('class')
                    data[label] = match.group('update')
                else:
                    data[label] = rest
            else:
                assert label not in data, "Non-unique line: data=%s, line='%s'" % (data, line)
                data[label] = rest

    return entries

def dump_dicts(fp, entries):
    writer = csv.DictWriter(fp, labels)
    writer.writeheader()
    writer.writerows(entries)

def parse_person_type(affil):
    if 'alum' in affil:
        return 'alum','full'
    elif affil in ('MIT undergrad', 'MIT student'):
        # fix "MIT Student" entries before final import
        return 'undergrad','mit-student'
    elif affil == 'MIT grad student':
        return 'grad','mit-student'
    elif affil == 'student':
        return 'none','student'
    elif affil == 'staff':
        return 'staff','full'
    else:
        assert affil == ''
        return 'none','full'

def load_row(row, system_people):
    person = squaresdb.membership.models.Person()
    person.name = row['name']
    person.email = row['email']
    person.level_id = '?'
    if row['class']:
        person.status_id = 'grad'
        tsclass, created = squaresdb.membership.models.TSClass.objects.get_or_create(
            label=row['class'], defaults=dict(coordinator=system_people['cc'])
        )
    else:
        person.status_id = 'member'
        tsclass = None
    person.mit_affil_id, person.fee_cat_id = parse_person_type(row['mitaffil'])
    person.save()
    if tsclass:
        TSClassMember = squaresdb.membership.models.TSClassMember
        TSClassMember.objects.create(student=person, clas=tsclass, pe=False)

@transaction.atomic
def load_csv(fp):
    reader = csv.DictReader(fp)
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
    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    if args.mode == 'legacy2csv':
        db = parse_to_dicts(sys.stdin)
        with open(args.csv, 'w') as fp:
            dump_dicts(fp, db)
    else:
        assert args.mode == 'csv2django'
        with open(args.csv, 'r') as fp:
            load_csv(fp)

if __name__ == '__main__':
    main()
