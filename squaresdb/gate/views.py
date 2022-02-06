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
import squaresdb.gate.forms as gate_forms
import squaresdb.membership.models as member_models

# Create your views here.
logger = logging.getLogger(__name__)


def _get_dance_dates(data):
    start = data.get('start_date')
    end = data.get('end_date')
    if not (start and end):
        return []
    ret = []
    cur = start
    while cur <= end:
        ret.append(cur)
        cur += datetime.timedelta(days=7)
    return ret

@transaction.atomic
def _make_sub_period(form, dance_dates, price_formset):
    new_period = form.save()
    price_formset.instance = new_period
    new_subprices = price_formset.save()
    price_scheme = form.cleaned_data['default_price_scheme']
    for date in dance_dates:
        time = datetime.datetime.combine(date, form.cleaned_data['time'])
        dance = gate_models.Dance(time=time, period=new_period,
                                  price_scheme=price_scheme)
        dance.save()
    return new_period

@permission_required(['gate.add_subscriptionperiod',
                      'gate.add_subscriptionperiodprice',
                      'gate.add_dance', ])
def new_sub_period(request):
    dance_dates = None
    new_period = None
    if request.method == 'POST':
        form = gate_forms.NewPeriodForm(request.POST)
        price_formset = gate_forms.new_period_prices_formset(request.POST)
        form_valid = form.is_valid() # Calling is_valid populates cleaned_data
        dance_dates = _get_dance_dates(form.cleaned_data)
        price_valid = price_formset.is_valid()
        if price_valid:
            for price_form in price_formset.forms:
                if not price_form.cleaned_data:
                    price_form.add_error('low', 'Price is required')
                    price_valid = False
        if form_valid and price_formset.is_valid():
            new_period = _make_sub_period(form, dance_dates, price_formset)
    else:
        form = gate_forms.NewPeriodForm()
        price_formset = gate_forms.new_period_prices_formset()

    context = dict(
        pagename='signin',
        form=form,
        price_formset=price_formset,
        dance_dates=dance_dates,
        new_period=new_period,
    )
    return render(request, 'gate/new_period.html', context)


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

def signin_annotate_button_class(dance, people, subscribers):
    """Annotate the people with their button class (paid/present status) for dance"""
    # Find people already marked as attending
    dance_payments = gate_models.DancePayment.objects.filter(for_dance=dance)
    payees_dance = set()
    for payment in dance_payments:
        payees_dance.add(payment.person_id)
    attendees = gate_models.Attendee.objects.filter(dance=dance)
    attendees_paid = set()  # already paid as required
    attendees_owing = set() # owe payment
    for attendee in attendees:
        if (attendee.person_id in payees_dance or
            attendee.person_id in subscribers or
            attendee.person.fee_cat.slug == "mit-student"):
            attendees_paid.add(attendee.person_id)
        else:
            attendees_owing.add(attendee.person_id)
    # Annotate each person with a button class for attendee status
    for person in people:
        if person.pk in attendees_paid:
            person.button_class = "btn-primary"
        elif person.pk in attendees_owing:
            person.button_class = "btn-warning"


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
        subscribers.add(subscription.person_id)
    signin_annotate_button_class(dance, people, subscribers)

    subscription_periods = gate_models.SubscriptionPeriod.objects
    subscription_periods = subscription_periods.filter(end_date__gte=datetime.date.today())
    subscription_periods = subscription_periods.order_by('start_date', 'slug')

    # Annotate each person with their status
    fee_cat_prices = build_price_matrix(dance, subscription_periods)
    for person in people:
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

def make_api_getters(params):
    """Return functions to get field/object or return error"""
    def get_object_or_respond(model, field, null_ok=False):
        try:
            pk = params[field]
            if null_ok and pk in (0, '0', ['0']):
                return None
            return model.objects.get(pk=pk)
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

    return get_object_or_respond, get_field_or_respond

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
    get_object_or_respond, get_field_or_respond = make_api_getters(params)


    # TODO: validate forms before submitting
    # TODO: support paying for upcoming subscription while have subscription to current dance
    # (currently will only show the "mark present" button for this, not the dropdown)
    # TODO: If somebody is marked present twice, suppress the dupes?
    # TODO: Change colors of names once they're checked in?
    # TODO: Table instead of alerts for showing checkins?
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

    data = {'msg':'Created'}
    data['payment'] = payment.pk if paid else 0
    data['attendee'] = attendee.pk if present else 0

    return JsonResponse(data=data, status=HTTPStatus.CREATED)

@permission_required('gate.signin_app')
@require_POST
@transaction.atomic
def signin_api_undo(request):
    params = request.POST
    logger.getChild('signin_api_undo').info('call: params=%s', params)
    get_object_or_respond, _get_field_or_respond = make_api_getters(params)

    try:
        payment = get_object_or_respond(gate_models.Payment, 'payment', null_ok=True)
        attendee = get_object_or_respond(gate_models.Attendee, 'attendee', null_ok=True)
        if not (payment or attendee):
            raise JSONFailureException('Nothing to undo')
        # TODO: Store creation timestamp, and only allow undoing (deleting)
        # recently-added ones
        # TODO: Add comment field (IIRC reversion has one?)
        if attendee:
            if attendee.payment != payment:
                msg = ("Attendee has associated payment, but supplied payment "
                       "doesn't match")
                raise JSONFailureException(msg)
            attendee.delete()
        if payment:
            payment.delete()
    except FailureResponseException as exc:
        return exc.response

    data = {'msg':'Created'}
    return JsonResponse(data=data, status=HTTPStatus.OK)

@permission_required('gate.books_app')
def books(request, pk):
    """Main books view"""
    dance = get_object_or_404(gate_models.Dance, pk=pk)
    period = dance.period
    payments = dance.payment_set.all()
    payments = payments.order_by('payment_type', 'amount', 'time')
    attendees = dance.attendee_set.all()

    # Total up amounts paid
    summary_keys = [
        'dancepayment__for_dance__time',
        'dancepayment__for_dance',
        'person__status__member',
        'person__fee_cat__name',
        'payment_type__name',
    ]
    summary_vals = dict(num=Count('person'), amount=Sum('amount'))
    payment_subtotals = dance.payment_set.values(*summary_keys).order_by(*summary_keys)
    payment_subtotals = payment_subtotals.annotate(**summary_vals)
    payment_totals = collections.Counter()
    for cat in payment_subtotals:
        payment_totals[cat['payment_type__name']] += cat['amount']
    print(payment_totals.items())

    context = dict(
        pagename='signin',
        dance=dance,
        period=period,
        payment_subtotals=reversed(payment_subtotals),
        payment_totals=payment_totals.items(),
        payments=payments,
        attendees=attendees,
    )
    return render(request, 'gate/books.html', context)
