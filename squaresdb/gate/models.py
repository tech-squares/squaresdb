from django.db import models
from django.utils import timezone

import reversion

import squaresdb.membership.models as member_models

# Create your models here.

@reversion.register
class SubscriptionPeriod(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name


@reversion.register
class SubscriptionPeriodPrice(models.Model):
    period = models.ForeignKey(SubscriptionPeriod, on_delete=models.PROTECT)
    fee_cat = models.ForeignKey(member_models.FeeCategory,
                                on_delete=models.PROTECT)
    low = models.IntegerField()
    high = models.IntegerField()


@reversion.register
class Dance(models.Model):
    time = models.DateTimeField()
    period = models.ForeignKey(SubscriptionPeriod, blank=True, null=True,
                               on_delete=models.PROTECT)

    def __str__(self):
        local = timezone.get_default_timezone()
        return self.time.astimezone(local).strftime('%a, %b %d, %Y @ %H:%M %Z')


@reversion.register
class PaymentMethod(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)
    in_gate = models.BooleanField()

    def __str__(self):
        return self.name


@reversion.register
class Payment(models.Model):
    person = models.ForeignKey(member_models.Person,
                               on_delete=models.PROTECT)
    at_dance = models.ForeignKey(Dance, blank=True, null=True,
                                 on_delete=models.PROTECT)
    time = models.DateTimeField(default=timezone.now)
    payment_type = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=5, decimal_places=2)
    fee_cat = models.ForeignKey(member_models.FeeCategory, blank=True, null=True,
                                on_delete=models.PROTECT)


@reversion.register
class SubscriptionPayment(Payment):
    period = models.ForeignKey(SubscriptionPeriod, on_delete=models.PROTECT)


@reversion.register
class DancePayment(Payment):
    for_dance = models.ForeignKey(Dance, on_delete=models.PROTECT)


@reversion.register
class Attendee(models.Model):
    person = models.ForeignKey(member_models.Person, on_delete=models.PROTECT)
    dance = models.ForeignKey(Dance, on_delete=models.PROTECT)
    # Blank means didn't pay. Could be their failure, or could be fine if they
    # get free admission as a student.
    payment = models.ForeignKey(Payment, blank=True, null=True,
                                on_delete=models.PROTECT)
