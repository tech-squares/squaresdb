import logging
import re

from django.core.validators import RegexValidator
from django.db import models

import reversion

from .backend import MailmanList

logger = logging.getLogger(__name__)

LIST_TYPES = dict(
    mailman=MailmanList
)
LIST_TYPE_CHOICES = ((name, name.capitalize()) for name in LIST_TYPES)

@reversion.register
class ListCategory(models.Model):
    # pylint:disable=duplicate-code
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)
    order = models.IntegerField(db_index=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "list categories"

@reversion.register
class MailingList(models.Model):
    list_type = models.CharField(choices=LIST_TYPE_CHOICES, max_length=10)
    category = models.ForeignKey(ListCategory, on_delete=models.CASCADE)
    order = models.IntegerField(db_index=True)
    LIST_NAME_RE = re.compile('^[a-z][a-z0-9-]*$')
    name = models.CharField(max_length=50, unique=True,
                            validators=[RegexValidator(regex=LIST_NAME_RE)])
    description = models.TextField()

    def get_list(self):
        if not self.LIST_NAME_RE.match(self.name):
            raise ValueError("invalid list name %s" % (self.name, ))
        return LIST_TYPES[self.list_type](self.name)

    def join_url(self):
        if self.list_type == 'mailman':
            return 'https://mailman.mit.edu/mailman/listinfo/%s' % (self.name, )
        return None

    def __str__(self):
        return f"{self.list_type}:{self.name}"

@reversion.register
class ListMember(models.Model):
    mail_list = models.ForeignKey(MailingList, on_delete=models.CASCADE)
    email = models.EmailField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['mail_list', 'email'], name='member'),
        ]
