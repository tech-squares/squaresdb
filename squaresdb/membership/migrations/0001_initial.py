# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from typing import List, Tuple

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ] # type: List[Tuple[str,str]]

    operations = [
        migrations.CreateModel(
            name='FeeCategory',
            fields=[
                ('slug', models.SlugField(serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=50)),
            ],
            options={
                'verbose_name_plural': 'fee categories',
            },
        ),
        migrations.CreateModel(
            name='MITAffil',
            fields=[
                ('slug', models.SlugField(serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('student', models.BooleanField()),
            ],
            options={
                'verbose_name': 'MIT affiliation',
            },
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254, blank=True)),
                ('join_date', models.DateTimeField(default=None, null=True, blank=True)),
                ('grad_year', models.IntegerField(default=None, null=True, blank=True)),
                ('last_marked_correct', models.DateTimeField(default=None, null=True, blank=True)),
                ('fee_cat', models.ForeignKey(to='membership.FeeCategory', on_delete=models.PROTECT)),
            ],
            options={
                'verbose_name_plural': 'people',
            },
        ),
        migrations.CreateModel(
            name='PersonComment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('body', models.TextField()),
                ('author', models.ForeignKey(related_name='comments_written', to='membership.Person', on_delete=models.PROTECT)),
                ('person', models.ForeignKey(related_name='comments', to='membership.Person', on_delete=models.PROTECT)),
            ],
        ),
        migrations.CreateModel(
            name='PersonStatus',
            fields=[
                ('slug', models.SlugField(serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('member', models.BooleanField()),
            ],
            options={
                'verbose_name_plural': 'person statuses',
            },
        ),
        migrations.CreateModel(
            name='SquareLevel',
            fields=[
                ('slug', models.SlugField(serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('order', models.IntegerField(db_index=True)),
            ],
        ),
        migrations.CreateModel(
            name='TSClass',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(max_length=20)),
                ('start_date', models.DateField(null=True, blank=True)),
                ('end_date', models.DateField(null=True, blank=True)),
            ],
            options={
                'verbose_name': 'Tech Squares class',
                'verbose_name_plural': 'Tech Squares classes',
            },
        ),
        migrations.CreateModel(
            name='TSClassAssist',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('role', models.CharField(max_length=255, blank=True)),
                ('assistant', models.ForeignKey(to='membership.Person', on_delete=models.PROTECT)),
                ('clas', models.ForeignKey(verbose_name='class', to='membership.TSClass', on_delete=models.PROTECT)),
            ],
            options={
                'verbose_name': 'Tech Squares class assistant',
            },
        ),
        migrations.CreateModel(
            name='TSClassMember',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('pe', models.BooleanField(verbose_name='taking class as PE student?')),
                ('clas', models.ForeignKey(verbose_name='class', to='membership.TSClass', on_delete=models.PROTECT)),
                ('student', models.ForeignKey(to='membership.Person', on_delete=models.PROTECT)),
            ],
            options={
                'verbose_name': 'Tech Squares class member',
            },
        ),
        migrations.AddField(
            model_name='tsclass',
            name='assistants',
            field=models.ManyToManyField(related_name='class_assist', through='membership.TSClassAssist', to='membership.Person'),
        ),
        migrations.AddField(
            model_name='tsclass',
            name='coordinator',
            field=models.ForeignKey(related_name='class_coord', to='membership.Person', on_delete=models.PROTECT),
        ),
        migrations.AddField(
            model_name='tsclass',
            name='students',
            field=models.ManyToManyField(related_name='classes', through='membership.TSClassMember', to='membership.Person'),
        ),
        migrations.AddField(
            model_name='person',
            name='level',
            field=models.ForeignKey(verbose_name='highest level', blank=True, to='membership.SquareLevel', on_delete=models.PROTECT),
        ),
        migrations.AddField(
            model_name='person',
            name='mit_affil',
            field=models.ForeignKey(verbose_name='MIT affiliation', to='membership.MITAffil', on_delete=models.PROTECT),
        ),
        migrations.AddField(
            model_name='person',
            name='status',
            field=models.ForeignKey(verbose_name='membership status', to='membership.PersonStatus', on_delete=models.PROTECT),
        ),
    ]
