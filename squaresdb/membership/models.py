import datetime

from django.contrib.auth.models import User
from django.db import models

import reversion

@reversion.register
class SquareLevel(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)
    order = models.IntegerField(db_index=True)

    def __unicode__(self):
        return self.name


@reversion.register
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


@reversion.register
class MITAffil(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)
    student = models.BooleanField()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = "MIT affiliation"


@reversion.register
class FeeCategory(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = "fee categories"


@reversion.register
class Person(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    level = models.ForeignKey(SquareLevel, verbose_name='highest level', blank=True)
    status = models.ForeignKey(PersonStatus, verbose_name='membership status')
    join_date = models.DateTimeField(default=None, null=True, blank=True)
    mit_affil = models.ForeignKey(MITAffil, verbose_name='MIT affiliation')
    grad_year = models.IntegerField(default=None, null=True, blank=True)
    fee_cat = models.ForeignKey(FeeCategory)
    last_marked_correct = models.DateTimeField(default=None, null=True, blank=True)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = "people"


@reversion.register
class PersonComment(models.Model):
    author = models.ForeignKey(Person)
    timestamp = models.DateTimeField(auto_now_add=True)
    body = models.TextField()
    person = models.ForeignKey(Person, related_name='comments')

    def __unicode__(self):
        return u"comment on %s (by %s)" % (self.person.name, self.author.name)


@reversion.register
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


@reversion.register
class TSClassAssist(models.Model):
    assistant = models.ForeignKey(Person)
    clas = models.ForeignKey(TSClass, verbose_name='class')
    role = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Tech Squares class assistant"


@reversion.register
class TSClassMember(models.Model):
    student = models.ForeignKey(Person)
    clas = models.ForeignKey(TSClass, verbose_name='class')
    pe = models.BooleanField(verbose_name='taking class as PE student?')

    class Meta:
        verbose_name = "Tech Squares class member"
