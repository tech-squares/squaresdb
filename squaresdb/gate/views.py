import collections
import csv
import datetime
import decimal
from http import HTTPStatus
import io
import logging

from typing import Any, Dict, List, Optional, Tuple

from django import forms
from django.contrib.auth.decorators import permission_required
from django.db import transaction
from django.db.models import Count, Sum
from django.db.models.query import QuerySet
# pylint doesn't recognize usage in type annotations
from django.http import HttpRequest, HttpResponse # pylint:disable=unused-import
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.views.generic import DetailView

import reversion

import squaresdb.gate.models as gate_models
import squaresdb.gate.forms as gate_forms
import squaresdb.membership.models as member_models

logger = logging.getLogger(__name__)

DANCE_NOWISH_WINDOW = datetime.timedelta(days=1)


def strtobool(string):
    """Convert "true" or "false" as strings to booleans"""
    if string == 'true':
        return True
    elif string == 'false':
        return False
    else:
        raise ValueError('string must be "true" or "false"')

### Make a new subscription period and associated dances

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
    price_formset.save()
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

### List dances and sub periods

def index(request):
    # Dances
    now = timezone.now()
    window = DANCE_NOWISH_WINDOW
    dances = gate_models.Dance.objects.filter(time__gt=now-window, time__lt=now+window)
    dances = dances.order_by('time')
    dances = dances.annotate(num_attendees=Count('attendee'))

    # Subscription Periods
    periods = gate_models.SubscriptionPeriod.objects.order_by('-end_date')
    periods = periods.annotate(num_dances=Count('dance'))

    context = dict(
        pagename='signin',
        cur_dances=dances,
        periods=periods,
    )
    return render(request, 'gate/index.html', context)


class SubPeriodView(DetailView): #pylint:disable=too-many-ancestors
    model = gate_models.SubscriptionPeriod
    context_object_name = 'period'

    def get_context_data(self, *args, **kwargs): #pylint:disable=arguments-differ
        context = super().get_context_data(*args, **kwargs)
        context['pagename'] = 'signin'

        dances = context['object'].dance_set
        dances = dances.order_by('time')
        dances = dances.annotate(num_attendees=Count('attendee'))
        context['dances'] = dances

        # Highlight dances that are roughly now
        now = timezone.now()
        context['min_date_highlight'] = now - DANCE_NOWISH_WINDOW
        context['max_date_highlight'] = now + DANCE_NOWISH_WINDOW

        return context

### Signin app

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
    people = member_models.Person.objects.exclude(status__slug='system')
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
            raise JSONFailureException(f'Could not find field {field}') from exc
        except model.DoesNotExist as exc:
            msg = f'Could not find match for {field}={params[field]}'
            raise JSONFailureException(msg) from exc

    def get_field_or_respond(converter, field):
        try:
            return converter(params[field])
        except KeyError as exc:
            raise JSONFailureException(f'Could not find field {field}') from exc
        except ValueError as exc:
            msg = f'Could not interpret field {field} ({params[field]})'
            raise JSONFailureException(msg) from exc
        except decimal.InvalidOperation as exc:
            msg = f'Could not interpret field {field} ({params[field]}) as decimal'
            raise JSONFailureException(msg) from exc

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

def _signin_api_paid(person: member_models.Person, dance: gate_models.Dance,
                     notes: str, params) -> gate_models.Payment:
    """Create payment record in the signin API"""
    get_object_or_respond, get_field_or_respond = make_api_getters(params)

    paid_amount = get_field_or_respond(decimal.Decimal, 'paid_amount')
    paid_method = get_object_or_respond(gate_models.PaymentMethod, 'paid_method')
    paid_for = get_field_or_respond(str, 'paid_for')

    payment: gate_models.Payment # populated as dance or sub payment in if below
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
        raise JSONFailureException('Unexpected value {paid_for=}')
    return payment

def _signin_api_present(person: member_models.Person, dance: gate_models.Dance,
                       payment: Optional[gate_models.Payment], data):
    """Create attendee record in the API"""
    defaults = dict(payment=payment)
    qs = gate_models.Attendee.objects
    attendee, created = qs.get_or_create(person=person, dance=dance, defaults=defaults)
    if created:
        data['attendee_created'] = True
    else:
        data['attendee_created'] = False
        if attendee.payment:
            data['msg'] = 'Success, attendee already existed, with payment'
        elif payment:
            attendee.payment = payment
            attendee.save()
            data['msg'] = 'Success, attendee already existed, but set payment'
    return attendee

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
    # TODO: If somebody is marked present twice, suppress the dupes?
    # TODO: add tests

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
        data = dict(msg="Success")
        if paid:
            payment = _signin_api_paid(person, dance, notes, params)

        if present:
            attendee = _signin_api_present(person, dance, payment, data)

    except FailureResponseException as exc:
        return exc.response

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
        # TODO: Only allow undoing (deleting) recently-added ones (based on
        # `time` field on both Payment and Attendee)
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

    data = {'msg':'Deleted'}
    return JsonResponse(data=data, status=HTTPStatus.OK)


### Books app

@permission_required('gate.books_app')
def books(request, pk):
    """Main books view"""
    dance = get_object_or_404(gate_models.Dance, pk=pk)
    period = dance.period
    payments = dance.payment_set.all()
    payments = payments.order_by('payment_type', 'amount', 'time')
    attendees = dance.attendee_set.order_by('person__name')
    num_mit = sum(1 if att.person.fee_cat.slug == 'mit-student' else 0
                  for att in attendees)

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
        num_mit=num_mit,
    )
    return render(request, 'gate/books.html', context)


### Subscription upload

def _build_period_label_obj_map(period_objs):
    """Build period label -> period map"""
    allow_periods = {}
    for period in period_objs:
        allow_periods[period.slug] = period
        allow_periods[period.slug.replace("-", "_")] = period
        # While transitioning over from old naming scheme
        year, _dash, season = period.slug.partition('-')
        allow_periods[season+year] = period
    return allow_periods

def _fill_squarespay_periods(row: Dict[str,str],
                             allow_periods: Dict[str,gate_models.SubscriptionPeriod],
                             errors: List[str]) \
            -> Optional[List[gate_models.SubscriptionPeriod]]:
    period_names = row['tuesday_subscriptions']
    if not period_names:
        return None
    try:
        periods = [allow_periods[period] for period in period_names.split(',')]
    except KeyError as exc:
        error = 'Unexpected period %s (full list: %s) for payment from "%s"' % \
                (exc, period_names, row['name'])
        logger.warning(error)
        errors.append(error)
        return None
    return periods

SQUARESPAY_NOTE_FIELDS = [("Name", "name"),
                         ("Email", "email"),
                         ("Virtual dances", "virtual_dances"),
                         ("Tuesday subscriptions", "tuesday_subscriptions"),
                         ("Rounds class", "rounds_class"),
                         ("Other items", "other_items"),
                         ("Amount", "amount"),
                         ("squares-pay SID", "webform_sid"),
                         ("Notes", "notes")]

def _fill_squarespay_note(row) -> str:
    lines = []
    for label, field in SQUARESPAY_NOTE_FIELDS:
        val = row[field] or "(none)"
        lines.append(f"{label}: {val}")
    return "\n".join(lines)

def _fill_squarespay_people(name_str, errors) -> List[member_models.Person]:
    names = [name.strip() for name in name_str.split(',')]
    if len(names) == 1:
        name_words = name_str.split()
        if len(name_words) == 4:
            first1, _and, first2, last = name_words
            names = [f"{first1} {last}", f"{first2} {last}"]
    people: List[member_models.Person] = []
    for name in names:
        try:
            person = member_models.Person.objects.get(name=name)
            people.append(person)
        except member_models.Person.DoesNotExist:
            errors.append("Person couldn't be found: %s" % (name, ))
    return people

def _fill_squarespay_sub_amount(total, sub_datas):
    """Allocate payment among people for a single sub payment"""
    amount = decimal.Decimal(total)/max(len(sub_datas), 1)
    for sub_data in sub_datas:
        sub_data['amount'] = amount

def _find_squarespay_subs_from_row(new_subs, errors, warns,
                                   allow_periods, row, payment_type) -> None:
    # pylint:disable=too-many-arguments
    assert row['paymentOption'] == 'card'
    if row['decision'] != 'ACCEPT':
        warn = 'Payment for "%s" had decision %s, ignoring' % (row['name'], row['decision'])
        warns.append(warn)
        return
    periods = _fill_squarespay_periods(row, allow_periods, errors)
    if periods is None:
        return
    notes = _fill_squarespay_note(row)
    people = _fill_squarespay_people(row['name'], errors)
    data = dict(at_dance=None, time=row['webform_completed_time'],
                payment_type=payment_type,
                notes=notes, periods=periods, )
    sub_datas = []
    for person in people:
        data2 = data.copy()
        data2.update(person=person, fee_cat=person.fee_cat)
        sub_datas.append(data2)
        # Add dictionaries to new_subs immediately; amount is still missing,
        # but we can fill that in later.
        new_subs.append((row, data2))
    _fill_squarespay_sub_amount(row['amount'], sub_datas)

def find_subs_from_upload(subs_file, form):
    """Processes payment data from squares-pay

    Notes on expected fields:
    webform_serial is per form, webform_sid is site-wide
    (per https://www.drupal.org/project/webform/issues/919832)

    We care about:
    webform_completed_time -- copied to payment.time
    name/email -- used to find person
    tuesday_subscriptions -- used to fill in periods
    amount -- used to fill in amount
    notes  -- used to fill part of notes
    paymentOption -- always expected to be "card", used for payment_type
    decision -- must be "ACCEPT"

    We always leave at_dance blank and fee_cat is the person's value.

    The payment.notes field is filled with the submitted notes, plus
    webform_sid, name, email, and other things paid for (virtual_dances,
    rounds_class, other_items).
    """

    allow_periods = _build_period_label_obj_map(form.cleaned_data['sub_periods'])

    payment_type = gate_models.PaymentMethod(slug='credit')

    subs_text = io.TextIOWrapper(subs_file) # binary mode -> text mode
    subs_text.readline() # First two lines aren't really headers
    subs_text.readline()
    reader = csv.DictReader(subs_text, delimiter='\t')
    new_subs = []
    errors = []
    warns = []
    for row in reader:
        _find_squarespay_subs_from_row(new_subs, errors, warns, allow_periods, row, payment_type)
    return new_subs, errors, warns


def _bulk_add_subs(request, new_subs=None, errors=None, warns=None):
    if new_subs:
        num_extras = len(new_subs)
    else:
        num_extras = 0
    SubPay = gate_models.SubscriptionPayment
    SubPayFormSet = forms.modelformset_factory(SubPay, # pylint:disable=invalid-name
                                               form=gate_forms.SubPayAddForm,
                                               extra=num_extras, can_delete=True)
    context = {}
    if new_subs is not None:
        formset = SubPayFormSet(initial=[data for pay, data in new_subs],
                                queryset=SubPay.objects.none())
        context['sub_formset'] = formset
        context['errors'] = errors
        context['warns'] = warns
    else:
        formset = SubPayFormSet(request.POST)
        if formset.is_valid():
            with reversion.create_revision(atomic=True):
                reversion.set_comment("bulk sub add")
                reversion.set_user(request.user)
                context['sub_instances'] = formset.save()
        else:
            context['sub_formset'] = formset
    return render(request, 'gate/sub_upload.html', context)

@permission_required('gate.add_subscriptionpayment')
def upload_subs(request):
    if request.method == 'POST':
        if 'submit_upload' in request.POST:
            form = gate_forms.SubUploadForm(request.POST, request.FILES)
            if form.is_valid():
                new_subs, errors, warns = find_subs_from_upload(request.FILES['file'], form)
                return _bulk_add_subs(request, new_subs, errors, warns)
        else:
            return _bulk_add_subs(request)

    else:
        form = gate_forms.SubUploadForm()
    return render(request, 'gate/sub_upload.html', {'upload_form': form})


### Bulk add subscriptions

def _bulk_sub_save_form(clean, period):
    subpays = []
    for person in clean['people']:
        data = dict(person=person, payment_type=clean['payment_type'],
                    amount=clean['amount'], fee_cat=person.fee_cat,
                    notes=clean['notes'])
        subpay = gate_models.SubscriptionPayment(**data)
        subpay.save()
        subpay.periods.add(period)
        subpays.append(subpay)
    return subpays


@permission_required('gate.add_subscriptionpayment')
def bulk_sub(request, slug):
    period = get_object_or_404(gate_models.SubscriptionPeriod, slug=slug)

    # Handle the form
    subpays = []
    if request.method == 'POST':
        form = gate_forms.BulkSubForm(request.POST)
        if form.is_valid():
            # Save
            with reversion.create_revision(atomic=True):
                reversion.set_comment("bulk sub add: " + form.cleaned_data['notes'])
                reversion.set_user(request.user)
                subpays = _bulk_sub_save_form(form.cleaned_data, period)

    else:
        form = gate_forms.BulkSubForm()

    # Find people who have paid already
    subscriptions = gate_models.SubscriptionPayment.objects
    subscriptions = subscriptions.filter(periods=period)
    subscribers = set()
    for subscription in subscriptions:
        subscribers.add(subscription.person_id)

    context = dict(form=form, subpays=subpays, subscribers=subscribers, period=period)
    return render(request, 'gate/bulk_sub.html', context)


### Voting members

class AnnoPerson(member_models.Person):
    """Person annotated with fields for the voting member viewed

    Largely exists for type-checking"""

    def __init__(self, *args: List[Any], **kwargs: Dict[str, Any]) -> None:
        super().__init__(*args, **kwargs)
        self.attend: Dict[int,gate_models.Attendee] = {}
        self.dance_pays: Dict[int,gate_models.DancePayment] = {}
        self.subs: Dict[str,gate_models.SubscriptionPayment] = {}
        self.dance_list: List[Tuple[str,bool]] = [] # list of attendee status per dance, in order

    class Meta:
        proxy = True

def person_table_annotate_people(people: QuerySet[AnnoPerson],
                                  dance_ids: List[int], sub_ids: List[int]) \
        -> QuerySet[AnnoPerson]:
    # Find the people
    people_dict: Dict[int, AnnoPerson] = {}
    for person in people:
        people_dict[person.pk] = person

    # Find attendance data
    attendees = gate_models.Attendee.objects.filter(person__in=people, dance__in=dance_ids)
    attendees = attendees.order_by('person', '-dance__time')
    for attendee in attendees:
        # This uses a *different* person object than we found above, so we
        # find the shared one in the dict we built above
        people_dict[attendee.person.pk].attend[attendee.dance_id] = attendee

    # Find dance payment data
    dance_pays = gate_models.DancePayment.objects.filter(person__in=people)
    dance_pays = dance_pays.filter(for_dance__in=dance_ids)
    for dance_pay in dance_pays:
        people_dict[dance_pay.person.pk].dance_pays[dance_pay.for_dance_id] = dance_pay

    # Find sub payment data
    sub_pays = gate_models.SubscriptionPayment.objects.filter(person__in=people)
    sub_pays = sub_pays.filter(periods__in=sub_ids)
    for sub_pay in sub_pays:
        for period in sub_pay.periods.all():
            people_dict[sub_pay.person.pk].subs[period.pk] = sub_pay

    return people

def _person_table_generate_table(people, dance_ids, sub_ids):
    """Populate dance_list for voting member table"""
    for person in people:
        for dance, period in zip(dance_ids, sub_ids):
            paid = (dance in person.dance_pays)
            # TODO: check price, not just hard-coded fee_cat
            sub = ((period in person.subs) or (person.fee_cat_id == 'mit-student'))
            if dance in person.attend:
                if paid or sub:
                    code = 'X'
                else:
                    code = 'O'
            else:
                if paid:
                    code = 'P'
                else:
                    code = ''
            data = (code, sub)
            person.dance_list.append(data)
        # This lets us use dictsort in the template
        person.dance_len = len(person.attend)

def _person_table_build_data(people_all, dance_objs):
    dance_ids = [dance.pk for dance in dance_objs]
    sub_ids = [dance.period_id for dance in dance_objs]
    people = person_table_annotate_people(people_all, dance_ids, sub_ids)
    _person_table_generate_table(people, dance_ids, sub_ids)

    # Render the page
    context = dict(
        pagename='signin',
        dances=dance_objs,
        people=people,
    )
    return context

@permission_required('gate.view_attendee')
def voting_members(request):
    # Find the dances
    # TODO: Allow choosing the right time range
    # TODO: Allow choosing individual dances
    # TODO: Automatically filter out non-Tuesday dances
    # TODO: Summer dances don't count towards the 15, but do count towards attendance numbers
    end = datetime.datetime.now()
    dance_qs = gate_models.Dance.objects.filter(time__lte=end).order_by('-time')
    dance_qs = dance_qs.select_related('period')
    dance_objs = list(reversed(dance_qs[:15]))
    people_all = AnnoPerson.objects.filter(status__member=True)
    context = _person_table_build_data(people_all, dance_objs)
    return render(request, 'gate/voting.html', context)

@permission_required('gate.view_attendee')
def paper_gate(request):
    # Find the dances
    now = datetime.datetime.now()
    dance_qs = gate_models.Dance.objects.select_related('period')
    dance_pre = list(reversed(dance_qs.filter(time__lte=now).order_by('-time')[:5]))
    dance_post = list(dance_qs.filter(time__gte=now).order_by('time')[:15])
    dance_objs = dance_pre + dance_post

    people_all = AnnoPerson.objects.exclude(frequency__slug__in=('never', 'unknown'))
    people_all = people_all.order_by('frequency__order', 'name')

    context = _person_table_build_data(people_all, dance_objs)
    return render(request, 'gate/paper_gate.html', context)

@permission_required(['gate.view_subscriptionpayment',
                      'membership.view_person', ])
def member_stats(request, slug):
    period = get_object_or_404(gate_models.SubscriptionPeriod, slug=slug)

    # Find affiliations
    mit_affil_objs = member_models.MITAffil.objects.all()
    mit_affils = {mit_affil.slug:mit_affil for mit_affil in mit_affil_objs}
    for mit_affil in mit_affils.values():
        mit_affil.free_fee_cat = []
        mit_affil.subscribers = []

    # Add by fee categories and subscribers
    for person in member_models.Person.objects.filter(fee_cat__slug='mit-student'):
        mit_affils[person.mit_affil_id].free_fee_cat.append(person)
    subs = gate_models.SubscriptionPayment.objects.filter(periods=period)
    subs = subs.select_related('person')
    for sub in subs:
        mit_affils[sub.person.mit_affil_id].subscribers.append(sub.person)

    # Render the page
    context = dict(
        pagename='signin',
        period=period,
        mit_affils=mit_affils,
    )
    return render(request, 'gate/member_stats.html', context)
