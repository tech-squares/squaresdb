import datetime

from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404, render

import squaresdb.gate.models as gate_models
import squaresdb.membership.models as member_models

# Create your views here.


# TODO: fix permission check
@permission_required('gate.signin_app')
def signin(request, slug):
    """Main gate view"""
    # Find all "real" people who attend sometimes
    period = get_object_or_404(gate_models.SubscriptionPeriod, slug=slug)
    people = member_models.Person.objects.exclude(frequency__slug='never')
    people = people.exclude(status__slug='system')
    people = people.order_by('frequency__order', 'name')
    people = people.select_related('fee_cat')

    # Find people who have paid already
    subscriptions = gate_models.SubscriptionPayment.objects.filter(period=period, person__in=people)
    # I thought that Django had a cache such that forcing `people` to be
    # fetched earlier would prevent the subscribers from being fetched
    # individually, but seemingly that's not true. selected_related solves this
    # for us, though.
    subscriptions = subscriptions.select_related('person')
    subscribers = set()
    for subscription in subscriptions:
        subscribers.add(subscription.person)

    # Annotate each person with their status
    for person in people:
        subscriber_letter = '+' if person in subscribers else '-'
        # TODO: better fee category abbreviation than just the first letter?
        person.signin_label = person.fee_cat.name[0] + subscriber_letter

    subscription_periods = gate_models.SubscriptionPeriod.objects
    subscription_periods = subscription_periods.filter(end_date__gte=datetime.date.today())
    subscription_periods = subscription_periods.order_by('start_date', 'slug')

    context = dict(
        pagename='signin',
        payment_methods=gate_models.PaymentMethod.objects.all(),
        subscription_periods=subscription_periods,
        period=period,
        people=people,
        subscribers=subscribers,
    )
    return render(request, 'gate/signin.html', context)
