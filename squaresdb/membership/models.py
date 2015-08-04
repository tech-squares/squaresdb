import datetime

from django.contrib.auth.models import User
from django.db import models

class SquareLevel(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)
    order = models.IntegerField(db_index=True)

    def __unicode__(self):
        return self.name


class PersonStatus(models.Model):
    # graduated Tech Squares class
    # admitted by EC
    # member, unknown method
    # prospective -- routinely attends, probably on mailing list, "on checkin sheet"
    # guest -- attended maybe once, plausibly/likely has multiple entries in DB
    # system? placeholder people

    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)
    member = models.BooleanField()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = "person statuses"


class MITAffil(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)
    student = models.BooleanField()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = "MIT affiliation"


class FeeCategory(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = "fee categories"


class Person(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    level = models.ForeignKey(SquareLevel, verbose_name='highest level', blank=True)
    status = models.ForeignKey(PersonStatus, verbose_name='membership status')
    join_date = models.DateTimeField(default=None, null=True, blank=True)
    mit_affil = models.ForeignKey(MITAffil, verbose_name='MIT affiliation')
    grad_year = models.IntegerField(default=None, null=True, blank=True)
    fee_cat = models.ForeignKey(FeeCategory)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = "people"


class PersonComment(models.Model):
    author = models.ForeignKey(User)
    timestamp = models.DateTimeField(auto_now_add=True)
    body = models.TextField()
    person = models.ForeignKey(Person)


class TSClass(models.Model):
    label = models.CharField(max_length=20)
    coordinator = models.ForeignKey(Person, related_name='class_coord')
    assistants = models.ManyToManyField('Person', through='TSClassAssist', related_name='class_assist')
    students = models.ManyToManyField('Person', through='TSClassMember', related_name='classes')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    def __unicode__(self):
        return self.label

    class Meta:
        verbose_name = "Tech Squares class"
        verbose_name_plural = "Tech Squares classes"


class TSClassAssist(models.Model):
    assistant = models.ForeignKey(Person)
    clas = models.ForeignKey(TSClass, verbose_name='class')
    role = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Tech Squares class assistant"


class TSClassMember(models.Model):
    student = models.ForeignKey(Person)
    clas = models.ForeignKey(TSClass, verbose_name='class')
    pe = models.BooleanField(verbose_name='taking class as PE student?')

    class Meta:
        verbose_name = "Tech Squares class member"
