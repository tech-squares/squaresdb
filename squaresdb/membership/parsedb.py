#!/usr/bin/env python

import collections
import csv
import sys

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

def parse(fp):
    entries = []
    data = {'name': []}
    codes = collections.Counter()
    for line in fp:
        line = line.strip()
        if not line:
            entries.append(data)
            data = {'name': []}
        elif line.startswith(r'.\"'):
            pass # comment line
        else:
            assert len(line) >= 2 and line[0] == '%', "unexpected line: %s" % (line, )
            code = line[1]
            label, space, rest = line.partition(' ')
            if code == 'A':
                data['name'].append(rest)
            else:
                assert code in ('D', 'E', 'N', 'O', 'S', 'K') or code not in data, "Non-unique line: data=%s, line='%s'" % (data, line)
                data[code] = rest
            codes.update(code)

    print codes
    return entries

def dump_names(entries):
    names = []
    for entry in entries:
        for name in entry['name']:
            first, split, last = name.rpartition(' ')
            names.append((last, first))

    names.sort()
    fields = ['last', 'first']
    writer = csv.writer(sys.stdout)
    writer.writerow(fields)
    writer.writerows(names)

if __name__ == '__main__':
    db = parse(sys.stdin)
    dump_names(db)
