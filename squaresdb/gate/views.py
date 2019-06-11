from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404, render

import squaresdb.gate.models as gate_models
import squaresdb.membership.models as member_models

# Create your views here.


# TODO: fix permission check
@permission_required('gate.signin_app')
def signin(request, slug):
    """Main gate view"""
    period = get_object_or_404(gate_models.SubscriptionPeriod, slug=slug)
    people = member_models.Person.objects.exclude(frequency__slug='never')
    people = people.exclude(status__slug='system')
    people = people.order_by('frequency__order', 'name')
    # TODO: make sure our query count is sane
    # See https://docs.djangoproject.com/en/2.2/ref/models/querysets/#django.db.models.query.QuerySet.prefetch_related

    # Find people who have paid already
    subscriptions = gate_models.SubscriptionPayment.objects.filter(period=period, person__in=people)
    subscribers = set()
    for subscription in subscriptions:
        subscribers.add(subscription.person)

    # Annotate each person with their status
    for person in people:
        subscriber_letter = '+' if person in subscribers else '-'
        # TODO: better fee category abbreviation than just the first letter?
        person.signin_label = person.fee_cat.name[0] + subscriber_letter

    context = dict(
        pagename='signin',
        period=period,
        people=people,
        subscribers=subscribers,
    )
    return render(request, 'gate/signin.html', context)
