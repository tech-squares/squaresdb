#!/usr/bin/env python

import collections
import csv
import sys

# Format:
# %A Name
# %D Class
# %N Email
# %K Frequency

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
