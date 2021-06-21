import collections
import datetime
import decimal
from distutils.util import strtobool
from http import HTTPStatus
import logging

from django.contrib.auth.decorators import permission_required
from django.db import transaction
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.views.generic import ListView

import squaresdb.gate.models as gate_models
import squaresdb.membership.models as member_models

# Create your views here.
logger = logging.getLogger(__name__)

class DanceList(ListView): #pylint:disable=too-many-ancestors
    queryset = gate_models.Dance.objects.select_related('period')

    def get_context_data(self, *args, **kwargs): #pylint:disable=arguments-differ
        context = super().get_context_data(*args, **kwargs)
        context['pagename'] = 'signin'
        return context


def build_price_matrix_col(fee_cat_prices, slug, price_set):
    """Fill in a column of the price matrix"""
    for price in price_set.select_related('fee_cat'):
        for_cat = fee_cat_prices[price.fee_cat.slug]
        for_cat['cat_name'] = price.fee_cat.name
        price_range = gate_models.format_price_range(price.low, price.high)
        for_cat['prices'][slug] = (price.low, price.high, price_range)


def build_price_matrix(dance, periods):
    """Build a matrix of fee category x product (dance or period)"""
    default = collections.OrderedDict()
    default['dance'] = None
    for period in periods:
        default[period.slug] = None
    matrix = collections.defaultdict(lambda: dict(prices=default.copy()))

    build_price_matrix_col(matrix, 'dance', dance.price_scheme.danceprice_set)
    for period in periods:
        build_price_matrix_col(matrix, period.slug, period.subscriptionperiodprice_set)

    # We convert matrix to a real dict, because otherwise when Django templates
    # check if there's an "items" key, the defaultdict will create that key...
    return dict(**matrix)

# TODO: fix permission check
@permission_required('gate.signin_app')
@ensure_csrf_cookie
def signin(request, pk):
    """Main gate view"""
    # Find all "real" people who attend sometimes
    dance = get_object_or_404(gate_models.Dance, pk=pk)
    past_dances = gate_models.Dance.objects.filter(time__lt=dance.time)
    past_dances = past_dances.order_by('-time')[:10]
    future_dances = gate_models.Dance.objects.filter(time__gt=dance.time)
    future_dances = future_dances.order_by('time')[:10]
    period = dance.period
    people = member_models.Person.objects.exclude(frequency__slug='never')
    people = people.exclude(status__slug='system')
    people = people.order_by('frequency__order', 'name')
    people = people.select_related('fee_cat', 'frequency')

    # Find people who have paid already
    subscriptions = gate_models.SubscriptionPayment.objects
    subscriptions = subscriptions.filter(periods=period, person__in=people)
    # I thought that Django had a cache such that forcing `people` to be
    # fetched earlier would prevent the subscribers from being fetched
    # individually, but seemingly that's not true. selected_related solves this
    # for us, though.
    subscriptions = subscriptions.select_related('person')
    subscribers = set()
    for subscription in subscriptions:
        subscribers.add(subscription.person)

    subscription_periods = gate_models.SubscriptionPeriod.objects
    subscription_periods = subscription_periods.filter(end_date__gte=datetime.date.today())
    subscription_periods = subscription_periods.order_by('start_date', 'slug')

    # Annotate each person with their status
    fee_cat_prices = build_price_matrix(dance, subscription_periods)
    for person in people:
        subscriber_letter = '+' if person in subscribers else '-'
        # TODO: better fee category abbreviation than just the first letter?
        person.signin_label = person.fee_cat.name[0] + subscriber_letter
        try:
            person.prices = fee_cat_prices[person.fee_cat.slug]['prices']
        except KeyError:
            logger.error("No prices for %s in scheme %s", person.fee_cat, dance.price_scheme)
            person.prices = None


    context = dict(
        pagename='signin',
        payment_methods=gate_models.PaymentMethod.objects.all(),
        subscription_periods=subscription_periods,
        dance=dance,
        past_dances=past_dances,
        future_dances=future_dances,
        period=period,
        price_matrix=fee_cat_prices,
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
# - for_dance: Dance
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
    #pylint:disable=too-many-locals,too-many-statements
    # I was going to take JSON input, but apparently jQuery prefers
    # form-encoded, and that seems fine too, so whatever
    params = request.POST
    logger.getChild('signin_api').info('call: params=%s', params)

    def get_object_or_respond(model, field):
        try:
            return model.objects.get(pk=params[field])
        except KeyError as exc:
            raise JSONFailureException('Could not find field %s' % (field, )) from exc
        except model.DoesNotExist as exc:
            raise JSONFailureException('Could not find match for %s=%s'
                                       % (field, params[field])) from exc

    def get_field_or_respond(converter, field):
        try:
            return converter(params[field])
        except KeyError as exc:
            raise JSONFailureException('Could not find field %s' % (field, )) from exc
        except ValueError as exc:
            raise JSONFailureException('Could not interpret field %s (%d)' %
                                       (field, params[field])) from exc
        except decimal.InvalidOperation as exc:
            raise JSONFailureException('Could not interpret field %s (%s) as decimal' %
                                       (field, params[field])) from exc

    # TODO: validate forms before submitting
    # TODO: actual undo support
    # TODO: support paying for upcoming subscription while have subscription to current dance
    # (currently will only show the "mark present" button for this, not the dropdown)
    # TODO: add tests

    # Beyond gate:
    # TODO: decent UI for creating subscription season
    # - "Create a subscription season"
    # - Provide start+end dates
    # - Provide "price scheme" ("normal", generally)
    # - Table for supplying low+high prices for each fee cat
    # - --> generate Dance objects, subscription period prices objects
    # - Can use the admin to delete dances that won't occur, or add anything
    #   non-Tuesday that's included

    try:
        person = get_object_or_respond(member_models.Person, 'person')
        dance = get_object_or_respond(gate_models.Dance, 'dance')

        present = get_field_or_respond(strtobool, 'present')
        paid = get_field_or_respond(strtobool, 'paid')

        notes = params.get('notes', '')
        if notes and not paid:
            # Notes live on the payment object
            raise JSONFailureException('Can only add a note if marking as paid')

        payment = None
        if paid:
            paid_amount = get_field_or_respond(decimal.Decimal, 'paid_amount')
            paid_method = get_object_or_respond(gate_models.PaymentMethod, 'paid_method')
            paid_for = get_field_or_respond(str, 'paid_for')
            if paid_for == 'dance':
                if 'for_dance' in params:
                    for_dance = get_object_or_respond(gate_models.Dance, 'for_dance')
                else:
                    for_dance = dance
                payment = gate_models.DancePayment(person=person, at_dance=dance,
                                                   payment_type=paid_method,
                                                   amount=paid_amount,
                                                   fee_cat=person.fee_cat,
                                                   for_dance=for_dance,
                                                   notes=notes, )
                payment.save()
            elif paid_for == 'sub':
                period_objs = gate_models.SubscriptionPeriod.objects
                period_slugs = params.getlist('paid_period[]')
                if not period_slugs:
                    raise JSONFailureException('Field paid_period[] was missing')
                periods = period_objs.filter(slug__in=period_slugs)
                if len(periods) != len(period_slugs):
                    raise JSONFailureException('Could not find some sub periods')
                payment = gate_models.SubscriptionPayment(person=person,
                                                          at_dance=dance,
                                                          payment_type=paid_method,
                                                          amount=paid_amount,
                                                          fee_cat=person.fee_cat,
                                                          notes=notes, )
                payment.save()
                payment.periods.set(periods)
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

@permission_required('gate.books_app')
def books(request, pk):
    """Main books view"""
    dance = get_object_or_404(gate_models.Dance, pk=pk)
    period = dance.period
    payments = dance.payment_set.all()
    payments = payments.order_by('payment_type', 'amount', 'time')
    attendees = dance.attendee_set.all()
    summary_keys = [
        'dancepayment__for_dance__time',
        'dancepayment__for_dance',
        'person__status__member',
        'person__fee_cat__name',
        'payment_type__name',
    ]
    summary_vals = dict(num=Count('person'), amount=Sum('amount'))
    payment_totals = dance.payment_set.values(*summary_keys).order_by(*summary_keys)
    payment_totals = payment_totals.annotate(**summary_vals)

    context = dict(
        pagename='signin',
        dance=dance,
        period=period,
        payment_totals=reversed(payment_totals),
        payments=payments,
        attendees=attendees,
    )
    return render(request, 'gate/books.html', context)
