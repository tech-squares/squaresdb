from django.db import models
from django.urls import reverse
from django.utils import timezone

import reversion

import squaresdb.membership.models as member_models
import squaresdb.money.models as money_models

# Create your models here.

def format_price_range(low, high):
    return f"${low}" if low == high else f"${low}-{high}"


@reversion.register
class SubscriptionPeriod(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()

    def get_absolute_url(self):
        return reverse('gate:sub-period', args=[self.slug])

    def __str__(self):
        return self.name


@reversion.register
class SubscriptionPeriodPrice(models.Model):
    period = models.ForeignKey(SubscriptionPeriod, on_delete=models.PROTECT)
    fee_cat = models.ForeignKey(member_models.FeeCategory,
                                on_delete=models.PROTECT)
    low = models.IntegerField()
    high = models.IntegerField()

    def __str__(self):
        tmpl = "Sub Price for %s in %s: %s"
        return tmpl % (self.fee_cat, self.period,
                       format_price_range(self.low, self.high))


@reversion.register
class DancePriceScheme(models.Model):
    name = models.CharField(max_length=50)
    notes = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name + ("" if self.active else " (inactive)")


@reversion.register
class DancePrice(models.Model):
    price_scheme = models.ForeignKey(DancePriceScheme, on_delete=models.PROTECT)
    fee_cat = models.ForeignKey(member_models.FeeCategory,
                                on_delete=models.PROTECT)
    low = models.IntegerField()
    high = models.IntegerField()

    def __str__(self):
        tmpl = "Dance Price for %s in %s: %s"
        return tmpl % (self.fee_cat, self.price_scheme,
                       format_price_range(self.low, self.high))


@reversion.register
class Dance(models.Model):
    time = models.DateTimeField()
    period = models.ForeignKey(SubscriptionPeriod, blank=True, null=True,
                               on_delete=models.PROTECT)
    price_scheme = models.ForeignKey(DancePriceScheme, on_delete=models.PROTECT)

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
    notes = models.TextField(blank=True)


@reversion.register
class SubscriptionPayment(Payment):
    periods = models.ManyToManyField(SubscriptionPeriod)


@reversion.register
class DancePayment(Payment):
    for_dance = models.ForeignKey(Dance, on_delete=models.PROTECT)


@reversion.register
class Attendee(models.Model):
    person = models.ForeignKey(member_models.Person, on_delete=models.PROTECT)
    dance = models.ForeignKey(Dance, on_delete=models.PROTECT)
    time = models.DateTimeField(default=timezone.now)
    # Blank means didn't pay at a time they were marked present
    # This:
    # - Could be their failure
    # - Could be fine if they get free admission as a student
    # - Could be fine if they have a regular subscription
    # - Could be fine if they paid when not being marked present, perhaps on
    #   another night.
    payment = models.ForeignKey(Payment, blank=True, null=True,
                                on_delete=models.PROTECT)
    # TODO: Add pay_method field? Values "none", "free", "sub", "dance",
    # reflecting whether they failed to pay, get admission free, have a
    # subscription, or paid for a single dance.
    # "Have they paid?" then becomes pay_method != none
    # Right now, figuring this out requires checking for a sub or dance
    # payment, and also *digging into the history* to figure out if their
    # fee category was mit-student *at the time*
    # Alternatively, record their fee category or the price their fee category
    # owed at time of purchase. This makes the read logic more complicated --
    # still need to check for a dance or sub -- but we don't need to update
    # Attendee records based on later payment.

    class Meta:
        permissions = (
            ("signin_app", "Can use signin app"),
            # In general, signin (gate) is more sensitive than books -- both
            # see who attended, but signin can additionally mark people as
            # having paid and see all members. As a result, gate may be
            # limited to only the person doing gate that night or similar,
            # whereas books may make sense to distribute more broadly.
            # It probably makes sense to give books to the gate user, but not
            # vice-versa.
            ("books_app", "Can use books app"),
        )


### (Online) Payments

# Most models live in the reusable-ish money app; these are the SquaresDB
# specific pieces

@reversion.register
class SubscriptionLineItem(money_models.LineItem):
    sub_period = models.ForeignKey(SubscriptionPeriod, on_delete=models.PROTECT)
    subscriber_name = models.CharField(max_length=50)
    person = models.ForeignKey(member_models.Person, on_delete=models.PROTECT, null=True)
