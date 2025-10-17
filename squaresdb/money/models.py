import secrets

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

import reversion

# This is envisioned as generic money/payment models that could be used outside
# SquaresDB

def default_nonce():
    return secrets.token_hex(8)

@reversion.register
class Transaction(models.Model):
    class Stage(models.IntegerChoices): # pylint:disable=too-many-ancestors
        CART = 10
        REVIEW = 40
        PAID = 50
        CANCEL = 60

    nonce = models.CharField(default=default_nonce, max_length=16)
    time = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(get_user_model(), on_delete=models.PROTECT,
                             blank=True, null=True, )
    person_name = models.CharField(max_length=50)
    email = models.EmailField()
    notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    stage = models.IntegerField(choices=Stage)

    def net_amount(self, ):
        # Note: Any Transaction with stage=paid should total to 0
        return sum(lineitem.amount for lineitem in self.lineitem_set.all())

    def first_name(self, ):
        names = self.person_name.rsplit(maxsplit=1)
        return names[0] if len(names) > 1 else ""

    def last_name(self, ):
        names = self.person_name.rsplit(maxsplit=1)
        return names[-1]

    def stage_label(self, ):
        return self.Stage(self.stage).label

# Any Product.high greater than this is treated as infinite
# This should align with the Product.high help text
MAX_AMOUNT = 10**4

@reversion.register
class LineItem(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT)
    # We should never need a line item over $10M...
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    account_name = models.CharField(max_length=255)
    label = models.CharField(max_length=255)
    notes = models.TextField(blank=True)

    # https://docs.djangoproject.com/en/5.2/topics/db/models/#model-inheritance
    # Not abstract, because it's useful to do operations like "add up all the line items"


@reversion.register
class CybersourceLineItem(LineItem):
    # Note that payment line items should generally have a negative amount
    receipt_post = models.JSONField()
    decision = models.CharField(max_length=50, blank=True)
    ref_number = models.CharField(max_length=50, blank=True)
    card_number = models.CharField(max_length=50, blank=True)
    card_type = models.CharField(max_length=50, blank=True)


@reversion.register
class ProductCategory(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)
    order = models.IntegerField(db_index=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "product categories"


@reversion.register
class Product(models.Model):
    slug = models.SlugField(primary_key=True)
    label = models.CharField(max_length=255)
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE)
    order = models.IntegerField(db_index=True)
    active = models.BooleanField(default=True)
    account_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, help_text="displayed to users")
    admin_notes = models.TextField(blank=True, help_text="internal item notes")
    low = models.DecimalField(max_digits=9, decimal_places=2)
    high = models.DecimalField(max_digits=9, decimal_places=2,
                               help_text="Use 9999 for unlimited")

    def price(self, ):
        """Returns the price if low==high, else None"""
        return self.low if self.low == self.high else None


@reversion.register
class ProductLineItem(LineItem):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    count = models.IntegerField()
    price_each = models.DecimalField(max_digits=9, decimal_places=2)
