# Generated by Django 2.2 on 2019-06-13 06:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gate', '0002_paymentmethod'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='attendee',
            options={'permissions': (('signin_app', 'Can use signin app'),)},
        ),
    ]
