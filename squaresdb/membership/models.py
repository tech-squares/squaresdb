import datetime
import logging
import random
import string

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
import django.utils.crypto

import reversion

logger = logging.getLogger(__name__)

@reversion.register
class SquareLevel(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)
    order = models.IntegerField(db_index=True)

    def __str__(self):
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

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "person statuses"


@reversion.register
class MITAffil(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)
    student = models.BooleanField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "MIT affiliation"


@reversion.register
class FeeCategory(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "fee categories"


@reversion.register
class Person(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    level = models.ForeignKey(SquareLevel, on_delete=models.PROTECT,
                              verbose_name='highest level', blank=True)
    status = models.ForeignKey(PersonStatus, on_delete=models.PROTECT,
                               verbose_name='membership status')
    join_date = models.DateTimeField(default=None, null=True, blank=True)
    mit_affil = models.ForeignKey(MITAffil, on_delete=models.PROTECT,
                                  verbose_name='MIT affiliation')
    grad_year = models.IntegerField(default=None, null=True, blank=True)
    fee_cat = models.ForeignKey(FeeCategory, on_delete=models.PROTECT)
    last_marked_correct = models.DateTimeField(default=None, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "people"


@reversion.register
class PersonComment(models.Model):
    author = models.ForeignKey(Person, on_delete=models.PROTECT,
                               related_name='comments_written')
    timestamp = models.DateTimeField(auto_now_add=True)
    body = models.TextField()
    person = models.ForeignKey(Person, on_delete=models.PROTECT,
                               related_name='comments')

    def __str__(self):
        return u"comment on %s (by %s)" % (self.person.name, self.author.name)


def personauthlink_default_secret():
    choices = string.ascii_lowercase+string.digits
    secret_len = 40
    rng = random.SystemRandom()
    return ''.join([rng.choice(choices) for i in range(secret_len)])

def personauthlink_default_expire_time():
    return timezone.now() + datetime.timedelta(minutes=15)

@reversion.register
class PersonAuthLink(models.Model):
    # Field definitions
    person = models.ForeignKey(Person, on_delete=models.PROTECT,
                               related_name='auth_links', db_index=True)
    secret = models.CharField(max_length=50, unique=True, default=personauthlink_default_secret)
    allowed_ip = models.GenericIPAddressField(blank=True, null=True, default=None)
    expire_time = models.DateTimeField(default=personauthlink_default_expire_time)
    # Need some kind of state hash -- changing password (err, do we have one?),
    # email, Django SECRET_KEY should all perhaps invalidate links
    state_hash = models.CharField(max_length=64)

    # Creation info
    create_user = models.ForeignKey(User, on_delete=models.PROTECT,
                                    related_name='auth_links_created')
    create_ip = models.GenericIPAddressField(blank=True, null=True)
    create_time = models.DateTimeField(auto_now_add=True)
    create_reason_basic = models.CharField(max_length=20)
    create_reason_detail = models.CharField(max_length=255)


    def create_state_hash(self):
        data = dict(
            email=self.person.email,
        )
        str_data = "email='%(email)s'" % data
        # Uses SECRET_KEY as the HMAC key by default
        hashed = django.utils.crypto.salted_hmac('PersonAuthLink', str_data)
        return hashed.hexdigest()

    def verify_state_hash(self):
        correct_hash = self.create_state_hash()
        # Doesn't use constant_time_compare because users can't supply a state
        # hash to check -- we're just using this to see if something's been
        # changed, so guessing character by character isn't a risk.
        return correct_hash == self.state_hash

    @classmethod
    def get_link(cls, secret, request_ip):
        """
        Get a PersonAuthLink and confirm its validity

        Returns a tuple, with elements:
        (1) Validity: True (valid) or False (invalid)
        (2) Object: PersonAuthLink object if the secret was found and None
            otherwise

        If validity is False but object is non-None, one should next typically
        call send_new_auth_link to generate a replacement.
        """
        try:
            link = cls.objects.get(secret=secret)
            # Got an object, so the secret matches. Now we just need to check
            # the other restrictions.
            if not link.verify_state_hash():
                logger.info("Bad state hash for %s", link)
                return False, link
            if link.allowed_ip and link.allowed_ip != request_ip:
                logger.info("Non-allowed IP for %s (allowed=%s, request=%s)", link, link.allowed_ip, request_ip)
                return False, link
            if not timezone.now() < link.expire_time:
                logger.info("Expired link for %s (expire time %s)", link, link.expire_time)
                return False, link
            else:
                return True, link
            expire_time = models.DateTimeField(default=personauthlink_default_expire_time)
        except cls.DoesNotExist:
            logger.info("could not find %s...", secret[:10])
            return False, None

    @classmethod
    def create_auth_link(cls, person, reason, detail, creator):
        link = cls(person=person, create_user=creator,
            create_reason_basic=reason, create_reason_detail=detail)
        link.state_hash = link.create_state_hash()
        return link

    class Meta:
        permissions = (
            ("bulk_create_personauthlink", "Can bulk create PersonAuthLinks"),
        )


@reversion.register
class TSClass(models.Model):
    label = models.CharField(max_length=20)
    coordinator = models.ForeignKey(Person, on_delete=models.PROTECT,
                                    related_name='class_coord')
    assistants = models.ManyToManyField('Person', through='TSClassAssist',
                                        related_name='class_assist')
    students = models.ManyToManyField('Person', through='TSClassMember',
                                      related_name='classes')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.label

    class Meta:
        verbose_name = "Tech Squares class"
        verbose_name_plural = "Tech Squares classes"


@reversion.register
class TSClassAssist(models.Model):
    assistant = models.ForeignKey(Person, on_delete=models.PROTECT)
    clas = models.ForeignKey(TSClass, on_delete=models.PROTECT,
                             verbose_name='class')
    role = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Tech Squares class assistant"


@reversion.register
class TSClassMember(models.Model):
    student = models.ForeignKey(Person, on_delete=models.PROTECT)
    clas = models.ForeignKey(TSClass, on_delete=models.PROTECT,
                             verbose_name='class')
    pe = models.BooleanField(verbose_name='taking class as PE student?')

    class Meta:
        verbose_name = "Tech Squares class member"
