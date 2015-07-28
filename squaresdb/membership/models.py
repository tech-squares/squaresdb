import datetime

from django.contrib.auth.models import User
from django.db import models

class SquareLevel(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)
    order = models.IntegerField(db_index=True)


class PersonStatus(models.Model):
    # graduated Tech Squares class
    # admitted by EC
    # prospective -- routinely attends, probably on mailing list, "on checkin sheet"
    # guest -- attended maybe once, plausibly/likely has multiple entries in DB
    # system? placeholder people

    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)
    member = models.BooleanField()

    class Meta:
        verbose_name_plural = "person statuses"


class MITAffil(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)
    student = models.BooleanField()

    class Meta:
        verbose_name = "MIT affiliation"


class FeeCategory(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)

    class Meta:
        verbose_name_plural = "fee categories"


class Person(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    level = models.ForeignKey(SquareLevel, verbose_name='highest level', blank=True)
    status = models.ForeignKey(PersonStatus)
    join_date = models.DateTimeField(default=None, null=True, blank=True)
    mit_affil = models.ForeignKey(MITAffil)
    grad_year = models.IntegerField(default=None, null=True, blank=True)
    fee_cat = models.ForeignKey(FeeCategory)


class PersonComment(models.Model):
    author = models.ForeignKey(User)
    timestamp = models.DateTimeField(auto_now_add=True)
    body = models.TextField()
    person = models.ForeignKey(Person)


class TSClass(models.Model):
    coordinator = models.ForeignKey(Person, related_name='class_coord')
    assistants = models.ManyToManyField('Person', through='TSClassAssist', related_name='class_assist')
    students = models.ManyToManyField('Person', through='TSClassMember', related_name='classes')
    label = models.CharField(max_length=20)
    start_date = models.DateField(blank=True)
    end_date = models.DateField(blank=True)


class TSClassAssist(models.Model):
    assistant = models.ForeignKey(Person)
    clas = models.ForeignKey(TSClass, verbose_name='class')
    role = models.CharField(max_length=255, blank=True)


class TSClassMember(models.Model):
    student = models.ForeignKey(Person)
    clas = models.ForeignKey(TSClass, verbose_name='class')
    pe = models.BooleanField(verbose_name='taking class as PE student?')
