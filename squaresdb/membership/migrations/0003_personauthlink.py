# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-02-26 08:49
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import squaresdb.membership.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('membership', '0002_member_choices'),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonAuthLink',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('secret', models.CharField(default=squaresdb.membership.models.personauthlink_default_secret, max_length=50, unique=True)),
                ('allowed_ip', models.GenericIPAddressField(blank=True, default=None, null=True)),
                ('expire_time', models.DateTimeField(default=squaresdb.membership.models.personauthlink_default_expire_time)),
                ('state_hash', models.CharField(max_length=64)),
                ('create_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('create_time', models.DateTimeField(auto_now_add=True)),
                ('create_reason_basic', models.CharField(max_length=20)),
                ('create_reason_detail', models.CharField(max_length=255)),
                ('create_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='auth_links_created', to=settings.AUTH_USER_MODEL)),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='auth_links', to='membership.Person')),
            ],
            options={
                'permissions': (('bulk_create_personauthlink', 'Can bulk create PersonAuthLinks'),),
            },
        ),
    ]
