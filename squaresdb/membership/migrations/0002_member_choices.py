# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from django.db import models, migrations

def create_people(apps, db_alias):
    User = apps.get_model('auth', 'User')
    user_objs = [User(
        username='importer@SYSTEM', email='squaresdb-importer@mit.edu',
        first_name='importer', last_name='SYSTEM',
    )]
    User.objects.using(db_alias).bulk_create(user_objs)

    people = [
        dict(name='placeholder class coordinator', email='squaresdb-placeholder-cc@mit.edu'),
    ]
    Person = apps.get_model('membership', 'Person')
    people_objs = []
    for person in people:
        people_objs.append(Person(name=person['name'], email=person['email'], level_id='none', status_id='system', mit_affil_id='none', fee_cat_id='full'))
    Person.objects.using(db_alias).bulk_create(people_objs)

def populate_choices_tables(apps, schema_editor):
    db_alias = schema_editor.connection.alias

    data = dict(
        SquareLevel=[
            dict(slug='?', name='Unknown', order=0),
            dict(slug='none', name='None', order=50),
            dict(slug='plus', name='Plus', order=150),
            dict(slug='a1', name='Advanced 1', order=320),
            dict(slug='a2', name='Advanced 2', order=360),
            dict(slug='c1', name='Challenge 1', order=420),
            dict(slug='c2', name='Challenge 2', order=440),
            dict(slug='c3a', name='Challenge 3A', order=460),
            dict(slug='c3b', name='Challenge 3B', order=470),
            dict(slug='c4', name='Challenge 4', order=480),
        ],
        PersonStatus=[
            dict(slug='grad',   name='graduated Tech Squares class', member=True),
            dict(slug='admit',  name='admitted by EC',          member=True),
            dict(slug='member', name='member (unknown method)', member=True),
            dict(slug='prospective', name='prospective',    member=False),
            dict(slug='guest',  name='guest',               member=False),
            dict(slug='system', name='system (internal)',   member=False),
        ],
        MITAffil=[
            dict(slug='undergrad',  name='undergrad',       student=True),
            dict(slug='grad',       name='grad student',    student=True),
            dict(slug='staff',      name='faculty/staff',   student=False),
            dict(slug='alum',       name='alum',            student=False),
            dict(slug='community',  name='community (spouse, retiree, special student, etc.)', student=False),
            dict(slug='none',       name='none',            student=False),
        ],
        FeeCategory=[
            dict(slug='mit-student',    name='MIT student'),
            dict(slug='student',        name='student / financial aid'),
            dict(slug='full',           name='full'),
        ],
    )

    for key, values in data.items():
        model = apps.get_model('membership', key)
        model.objects.using(db_alias).bulk_create([
            model(**kwargs) for kwargs in values
        ])

    create_people(apps, db_alias)


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0001_initial'),
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.RunPython(populate_choices_tables),
    ]
