import datetime
from decimal import Decimal
from distutils.util import strtobool
from http import HTTPStatus
import logging

from django.contrib.auth.decorators import permission_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

import squaresdb.gate.models as gate_models
import squaresdb.membership.models as member_models

# Create your views here.


# TODO: fix permission check
@permission_required('gate.signin_app')
@ensure_csrf_cookie
def signin(request, slug):
    """Main gate view"""
    # Find all "real" people who attend sometimes
    period = get_object_or_404(gate_models.SubscriptionPeriod, slug=slug)
    people = member_models.Person.objects.exclude(frequency__slug='never')
    people = people.exclude(status__slug='system')
    people = people.order_by('frequency__order', 'name')
    people = people.select_related('fee_cat', 'frequency')

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

class FailureResponseException(Exception):
    def __init__(self, response):
        super().__init__()
        self.response = response

class JSONFailureException(FailureResponseException):
    def __init__(self, msg):
        response = JsonResponse(data={'msg':msg}, status=HTTPStatus.BAD_REQUEST)
        super().__init__(response)
        self.msg = msg

# Fields
# - person: Person
# - dance: Dance
# - present: bool
# - paid: bool
# - paid_amount: int
# - paid_method: PaymentMethod ({cash,check,credit})
# - paid_for: {dance,sub}
# - paid_period: SubscriptionPeriod

# TODO: fix permission check
@permission_required('gate.signin_app')
@require_POST
@transaction.atomic
def signin_api(request):
    #pylint:disable=too-many-locals
    # I was going to take JSON input, but apparently jQuery prefers
    # form-encoded, and that seems fine too, so whatever
    params = request.POST
    logger = logging.getLogger(__name__).getChild('signin_api')
    logger.info('call: params=%s', params)

    def get_object_or_respond(model, field):
        try:
            return model.objects.get(pk=params[field])
        except KeyError:
            raise JSONFailureException('Could not find field %s' % (field, ))
        except model.DoesNotExist:
            raise JSONFailureException('Could not find match for %s=%s' % (field, params[field]))

    def get_field_or_respond(converter, field):
        try:
            return converter(params[field])
        except KeyError:
            raise JSONFailureException('Could not find field %s' % (field, ))
        except ValueError:
            raise JSONFailureException('Could not interpret field %s (%d)' %
                                       (field, params[field]))

    # TODO: support paying for past weeks
    # TODO: support payments without being present (eg, if somebody pays for their spouse)
    # TODO: default payment amounts (subscriptions and regular)
    # TODO: schema updates (see todos elsewhere)
    # TODO: correctly identify which dance
    # TODO: use reasonable URL (probably dance ID)

    # Beyond gate:
    # TODO: decent UI for creating subscription season
    # TODO: books UI

    try:
        person = get_object_or_respond(member_models.Person, 'person')
        dance = get_object_or_respond(gate_models.Dance, 'dance')

        present = get_field_or_respond(strtobool, 'present')
        paid = get_field_or_respond(strtobool, 'paid')

        payment = None
        if paid:
            paid_amount = get_field_or_respond(Decimal, 'paid_amount')
            paid_method = get_object_or_respond(gate_models.PaymentMethod, 'paid_method')
            paid_for = get_field_or_respond(str, 'paid_for')
            if paid_for == 'dance':
                payment = gate_models.DancePayment(person=person, at_dance=dance,
                                                   payment_type=paid_method,
                                                   amount=paid_amount,
                                                   fee_cat=person.fee_cat,
                                                   for_dance=dance, )
                payment.save()
            elif paid_for == 'sub':
                period_objs = gate_models.SubscriptionPeriod.objects
                period_slugs = params.getlist('paid_period[]')
                if not period_slugs:
                    raise JSONFailureException('Field paid_period[] was missing')
                periods = period_objs.filter(slug__in=period_slugs)
                if len(periods) != len(period_slugs):
                    raise JSONFailureException('Could not find some sub periods')
                for period in reversed(periods):
                    # TODO: make SubPayment a 1:N, not 1:1
                    payment = gate_models.SubscriptionPayment(person=person,
                                                              at_dance=dance,
                                                              payment_type=paid_method,
                                                              amount=paid_amount,
                                                              fee_cat=person.fee_cat,
                                                              period=period, )
                    payment.save()
            else:
                raise JSONFailureException('Unexpected value %s for paid_for' % (paid_for, ))

        if present:
            attendee = gate_models.Attendee(person=person, dance=dance, payment=payment)
            attendee.save()

    except FailureResponseException as exc:
        return exc.response

    return JsonResponse(
        data={'msg':'Created'},
        status=HTTPStatus.CREATED,
    )
