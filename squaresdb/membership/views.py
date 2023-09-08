"""
Views for Tech Squares DB membership functionality
"""

import csv
import datetime
import io
import logging

from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core import mail
from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, ListView

import reversion
from social_django.models import UserSocialAuth

import squaresdb.gate.models as gate_models
import squaresdb.gate.views as gate_views
import squaresdb.mailinglist.models as mail_models
import squaresdb.membership.models
mem_models = squaresdb.membership.models

logger = logging.getLogger(__name__)


def mailto_link(addr):
    """Generate HTML for mailto link to an address"""
    return "<a href='mailto:%s'>%s</a>" % (addr, addr)


@permission_required('membership.view_person')
def view_person(request, pk):
    """Simple view to display a person"""
    person = get_object_or_404(squaresdb.membership.models.Person, pk=pk)
    return render(request, 'membership/person_detail.html', dict(person=person))


def format_date(date):
    """Format a possible date for end users"""
    if date:
        return date.strftime("%B %d, %Y")
    else:
        return "unknown"


def person_context_dict(person):
    """Generate a context dict for substitution in a template string
    """
    data = {}
    for field in 'name email'.split(' '):
        data['person_'+field] = getattr(person, field)
    data['person_level'] = person.level.name
    data['person_frequency'] = person.frequency.name
    data['person_member_status'] = person.status.full_str()
    data['person_join_date'] = format_date(person.join_date)
    data['person_mit_affil'] = person.mit_affil.full_str()
    data['person_grad_year'] = person.grad_year or "unknown or N/A"
    data['person_fee_cat'] = person.fee_cat
    return data

class PersonForm(forms.ModelForm):
    """Form to edit a Person"""
    mark_correct_help = ("If your information is correct, please check " +
                         "this box so we know how recent the information is.")
    mark_correct = forms.BooleanField(required=False, help_text=mark_correct_help)
    contact_html = mailto_link('squares-db-request@mit.edu')
    confirm_email_help = ("If you are changing your email address, please "
                          "enter it again to confirm that it is correct. " +
                          "Note that if you use an incorrect email address, " +
                          "you may unable to further update your information " +
                          "without contacting " + contact_html +
                          " for assistance.")
    confirm_email = forms.CharField(required=False, help_text=confirm_email_help)

    def clean(self):
        cleaned_data = super().clean()
        old_email = self.instance.email
        new_email = cleaned_data.get("email")
        confirm_email = cleaned_data.get("confirm_email")
        if new_email not in (old_email, confirm_email): # email needs to be unchanged, or confirmed
            error = "Since you're changing your email, you need to confirm the new address"
            self.add_error('confirm_email', error)

    class Meta: #pylint:disable=too-few-public-methods,missing-docstring
        model = squaresdb.membership.models.Person
        fields = ['name', 'email', 'confirm_email', 'level', 'frequency']

        # last_marked_correct gets special handling: we have a checkbox, and
        # update the value to the current time if it's checked.

        # Some fields can only be edited by the officers. They're hardcoded
        # in the template, rather than listed here in PersonForm.
        # Officer-only fields: status, join_date, mit_affil, grad_year, fee_cat

        # fee_cat should perhaps be semi-editable: changing to a more
        # expensive category should be self-service, but switching to a less
        # expensive category should require emailing the treasurer (probably
        # not emailing the normal update list). However, that's not currently
        # implemented, those there's a bunch of text about it in the template.


# TODO: allow self-service creation of links
# TODO: deployment story (given scripts.mit.edu doesn't support Py3.5+ now)


UPDATE_EMAIL_TEMPLATE = """
Hi %(person_name)s,

Thank you for updating your entry in the Tech Squares Membership Database. Your new information is:
Name:                   %(person_name)s
Email:                  %(person_email)s
Highest level:          %(person_level)s
Attendance frequency:   %(person_frequency)s
Membership status:      %(person_member_status)s
Member since:           %(person_join_date)s
MIT affiliation:        %(person_mit_affil)s
MIT grad year:          %(person_grad_year)s
Fee category:           %(person_fee_cat)s

Thanks,
Tech Squares
"""

def _edit_person_attendee(person, subs):
    sub_ids = set()
    for sub in subs:
        sub_ids.update(per.slug for per in sub.periods.all())

    # Attendance
    anno_people = gate_views.AnnoPerson.objects.filter(pk=person.pk)
    dance_cutoff = timezone.now() - datetime.timedelta(weeks=26)
    dances = gate_models.Dance.objects.filter(time__gte=dance_cutoff)
    dances = dances.select_related('price_scheme', 'period')
    dances = dances.order_by('-time')
    dance_ids = [dance.pk for dance in dances]
    anno_people = gate_views.person_table_annotate_people(anno_people,
                                                          dance_ids, sub_ids)
    # Populate attendee list
    anno_person = anno_people[0]
    attendees = []
    for dance in dances:
        attendee = anno_person.attend.get(dance.pk)
        if attendee:
            attendees.append(attendee)
            if person.fee_cat.slug == 'mit-student':
                attendee.paid = 'MIT student'
            elif attendee.dance.price_scheme.name == 'free':
                attendee.paid = 'free dance'
            elif dance.pk in anno_person.dance_pays:
                attendee.paid = 'paid at dance'
            elif attendee.dance.period and attendee.dance.period.slug in sub_ids:
                attendee.paid = 'subscription'
            else:
                attendee.paid = 'not paid'

    return attendees

def _edit_person_form(request, person):
    initial = {}
    msg = None
    old_email = person.email
    if request.method == 'POST': # If the form has been submitted...
        # A form bound to the POST data
        form = PersonForm(
            request.POST, request.FILES,
            instance=person,
        )

        if form.is_valid(): # All validation rules pass
            request_obj = form.save(commit=False)
            if form.cleaned_data['mark_correct']:
                request_obj.last_marked_correct = timezone.now()

            # Send confirmation email
            email_body = UPDATE_EMAIL_TEMPLATE % person_context_dict(request_obj)
            email = mail.EmailMessage(subject="Tech Squares MemberDB update",
                                      body=email_body,
                                      to=set([request_obj.email, old_email]))
            mail.get_connection().send_messages([email])

            # Actually save the object
            request_obj.save()
            form.save_m2m()
            msg = "Thanks for editing!"
        else:
            msg = "Validation failed. See below for details."
    else:
        form = PersonForm(instance=person, initial=initial, ) # An unbound form
    return form, msg

def edit_person_obj(request, person):
    """Helper to edit a Person

    The user calling the function is assumed to have permission to edit the
    Person passed -- callers are responsible for identifying the correct
    Person and checking authz.
    """

    # General info
    form, msg = _edit_person_form(request, person)

    # Subscriptions and attendance
    subs = gate_models.SubscriptionPayment.objects.filter(person=person)
    subs = subs.order_by('-time')[:8]
    sub_periods = sorted([per for sub in subs for per in sub.periods.all()],
                         key=lambda per: per.start_date, reverse=True)
    attendees = _edit_person_attendee(person, subs)

    # Mailing lists
    mail_lists = (mail_models.MailingList.objects.select_related('category')
                             .order_by('category__order', 'order'))
    member_objs = mail_models.ListMember.objects.filter(email=person.email)
    member_lists = set(obj.mail_list_id for obj in member_objs)
    for mail_list in mail_lists:
        mail_list.is_member = mail_list.pk in member_lists

    context = dict(
        person=person,
        form=form,
        mail_lists=mail_lists,
        sub_periods=sub_periods,
        attendees=attendees,
        msg=msg,
        pagename='person-edit',
    )
    return render(request, 'membership/person_self_edit.html', context)


@login_required
def edit_user_person(request, person_id=None):
    """Edit a Person corresponding to the logged-in user
    """
    emails = []
    if request.user.email:
        emails.append(request.user.email)

    # TODO: extract email addresses from social accounts, not just Django user
    # record?
    # Email address doesn't seem readily available at this stage??
    social = UserSocialAuth.get_social_auth_for_user(request.user)
    logger.info("social=%s", social)
    if social:
        logger.info("social[0]=%s", social[0].__dict__)

    # Find the people record
    people = squaresdb.membership.models.Person.objects.filter(email__in=emails)
    if person_id:
        people = people.filter(pk=person_id)

    # Edit the people record
    if len(people) == 1:
        person = people[0]
        return edit_person_obj(request, person)
    elif people:
        context = {
            'pagename':'person-edit',
            'people':people,
        }
        return render(request, 'membership/PersonUser/choose.html', context)
    else:
        return render(request, 'membership/PersonUser/unknown.html')


PERSONAUTHLINK_RESEND_TEMPLATE = """Hi %(person_name)s,

Your requested link for editing your Tech Squares Membership DB entry is:

    %(link)s

If you did not request this, please let us know at squares-db-request@mit.edu.

Thanks,
Tech Squares
"""

def resend_personauthlink(request, old_link):
    """Resend an expired or otherwise old PersonAuthLink"""
    # Make new link
    new_link = squaresdb.membership.models.PersonAuthLink.create_auth_link(
        old_link.person, reason='ResendPersonAuthLink',
        detail='from %d' % old_link.pk, creator=request.user,
    )
    new_link.create_ip = request.META['REMOTE_ADDR']
    new_link.save()

    # Send email
    data = {}
    data['person_name'] = new_link.person.name
    link_path = reverse('membership:person-link', args=[new_link.secret])
    data['link'] = request.build_absolute_uri(link_path)
    email_body = PERSONAUTHLINK_RESEND_TEMPLATE % data
    email_subj = "New link to update Tech Squares Membership DB"
    email = mail.EmailMessage(subject=email_subj, body=email_body,
                              to=[new_link.person.email])
    connection = mail.get_connection()
    connection.send_messages([email])


def edit_person_personauthlink(request, secret):
    """Edit a Person based on a PersonAuthLink

    If a correct PersonAuthLink secret is provided, allow editing that Person.
    If a real but invalid (eg, expired or tampered with) PersonAuthLink is
    supplied, allow generating a replacement. Otherwise, report an error.
    """
    request_ip = request.META['REMOTE_ADDR']
    valid, link = squaresdb.membership.models.PersonAuthLink.get_link(secret, request_ip)
    if valid:
        return edit_person_obj(request, link.person)
    else:
        if link:
            if request.GET.get('resend', '0') == '1':
                resend_personauthlink(request, link)
                context = dict(
                    pagename='person-edit',
                )
                return render(request, 'membership/PersonAuthLink/resent.html', context)
            else:
                context = dict(
                    secret=secret,
                    pagename='person-edit',
                )
                return render(request, 'membership/PersonAuthLink/invalid.html', context)
        else:
            return render(request, 'membership/PersonAuthLink/unknown.html')


class BulkPersonAuthLinkCreationForm(forms.Form):
    """Form to mail-merge out a bunch of PersonAuthLinks"""
    # Ideally, we'd use a Django template, but the security story there seems
    # dubious.
    default_template = """Hi %(person_name)s,

The Tech Squares Membership DB is moving online. You can update (much of) your information at:

    %(link)s

That page will also let you tell us that your information is correct -- until you do, we may continue to follow up with you, so we appreciate you visiting the page, even if your information is right already.

Your current information is:
Name:                   %(person_name)s
Email:                  %(person_email)s
Highest level:          %(person_level)s
Attendance frequency:   %(person_frequency)s

To update the following information, please email squares-db-request@mit.edu:
Membership status:  %(person_member_status)s
Member since:       %(person_join_date)s
MIT affiliation:    %(person_mit_affil)s
MIT grad year:      %(person_grad_year)s
Fee category:       %(person_fee_cat)s

Thanks,
Tech Squares
"""

    reason = forms.CharField()
    expire_in = forms.ChoiceField(choices=((-1, "no link"),
                                           (15, "15 minutes"),
                                           (60*24, "1 day"),
                                           (60*24*3, "3 days"),
                                           (60*24*7, "1 week")),
                                  help_text="How long before links should expire?",
                                  initial=60*24*3)
    subject = forms.CharField(initial='Tech Squares Membership Database')
    reply_to = forms.EmailField(required=False)
    template = forms.CharField(initial=default_template, widget=forms.Textarea)
    people_qs = squaresdb.membership.models.Person.objects.order_by('name')
    people = forms.ModelMultipleChoiceField(queryset=people_qs)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reason'].widget.attrs['size'] = 80
        self.fields['subject'].widget.attrs['size'] = 80
        self.fields['template'].widget.attrs['rows'] = 20
        self.fields['template'].widget.attrs['cols'] = 80

    def send_emails(self, request):
        """Format and send the PersonAuthLink emails"""
        msgs = []
        no_email = []
        for person in self.cleaned_data['people']:
            if not person.email:
                no_email.append(person)
                continue
            data = person_context_dict(person)

            if int(self.cleaned_data['expire_in']) > 0:
                # Create the link
                link = squaresdb.membership.models.PersonAuthLink.create_auth_link(
                    person, reason='BulkPersonAuthLinkCreation',
                    detail=self.cleaned_data['reason'], creator=request.user,
                )
                expire_minutes = int(self.cleaned_data['expire_in'])
                expire_interval = datetime.timedelta(minutes=expire_minutes)
                link.expire_time = timezone.now() + expire_interval
                link.create_ip = request.META['REMOTE_ADDR']
                link.save()
                link_url = reverse('membership:person-link', args=[link.secret])
                data['link'] = request.build_absolute_uri(link_url)

            # Create the email
            # TODO: Better error if no link was created but %(link)s or similar is used
            email_body = self.cleaned_data['template'] % data
            emails = [email.strip() for email in person.email.split(',')]
            msg = mail.EmailMessage(subject=self.cleaned_data['subject'],
                                    body=email_body, to=emails)
            if self.cleaned_data['reply_to']:
                msg.reply_to = [self.cleaned_data['reply_to']]
            msgs.append(msg)
        connection = mail.get_connection()
        connection.send_messages(msgs)
        return no_email


@permission_required('membership.bulk_create_personauthlink')
def create_personauthlinks(request):
    """View to bulk create and mail merge out PersonAuthLinks"""
    msg = ''
    people = None
    no_email = None
    if request.method == 'POST': # If the form has been submitted...
        form = BulkPersonAuthLinkCreationForm(
            request.POST,
        )

        if form.is_valid(): # All validation rules pass
            no_email = form.send_emails(request)
            msg = "Mail merged %d messages" % (len(form.cleaned_data['people']), )
            people = form.cleaned_data['people']
    else:
        initial = {}
        if 'people' in request.GET:
            people = request.GET['people'].split(',')
            initial['people'] = people
        if request.GET.get('link') == '0':
            initial['expire_in'] = -1
        form = BulkPersonAuthLinkCreationForm(initial=initial) # An unbound form
    context = dict(
        form=form,
        msg=msg,
        people=people,
        no_email=no_email,
        pagename='personauthlink-bulkcreate',
    )
    return render(request, 'membership/personauthlink_bulkcreate.html', context)


class ClassList(PermissionRequiredMixin, ListView): #pylint:disable=too-many-ancestors
    permission_required = ('membership.view_tsclass', )
    model = squaresdb.membership.models.TSClass
    queryset = (model.objects.select_related('coordinator')
            .annotate(num_students=Count('students'))
            .order_by('-start_date'))

    def get_context_data(self, *args, **kwargs): #pylint:disable=arguments-differ
        context = super().get_context_data(*args, **kwargs)
        context['pagename'] = 'tsclass'
        context['now'] = datetime.date.today()
        return context


class ClassDetail(PermissionRequiredMixin, DetailView):
    permission_required = ('membership.view_tsclass',
                           'membership.view_tsclassassist',
                           'membership.view_tsclassmember',
                           'membership.view_person', )
    model = squaresdb.membership.models.TSClass

    def get_context_data(self, *args, **kwargs): #pylint:disable=arguments-differ
        context = super().get_context_data(*args, **kwargs)
        context['pagename'] = 'tsclass'
        print(context['object'].assistants.through)
        return context


class ImportClassForm(forms.ModelForm):
    student_csv = forms.FileField()

    class Meta:
        model = squaresdb.membership.models.TSClass
        fields = ['label', 'start_date', 'end_date', 'coordinator', ]


def _import_class_get_mit_affils():
    # Fee category
    mit_fee = mem_models.FeeCategory.objects.get(slug='mit-student')
    full_fee = mem_models.FeeCategory.objects.get(slug='full')

    # MIT affiliations
    mit_affils_list = mem_models.MITAffil.objects.all()
    mit_affils = {obj.slug:obj for obj in mit_affils_list}
    for mit_affil in mit_affils.values():
        mit_affil.fee_cat = mit_fee if mit_affil.student else full_fee

    return mit_affils


def _import_class_save_row(row, tsclass, defaults, mit_affils):
    mit_affil = mit_affils[row['MIT affiliation?']]
    name = row['First Name'] + " " + row['Last Name']
    grad = int(row['Grad year']) if row['Grad year'] else None
    args = dict(name=name, email=row['Email'], mit_affil=mit_affil,
                grad_year=grad, fee_cat=mit_affil.fee_cat, **defaults)
    person = mem_models.Person(**args)
    person.save()

    is_pe = {'TRUE': True, 'FALSE': False}[row['PE']]
    member = mem_models.TSClassMember(student=person, clas=tsclass, pe=is_pe)
    member.save()

    return person, member


def _import_class_save_form(data, tsclass):
    """Processes new club member data

    Expected fields:
    First Name
    Last Name
    MIT affiliation? - match slug column (https://squaresdb.mit.edu/admin/membership/mitaffil/)
    Email
    Grad year
    PE - true/false
    """

    # Prep various fields
    plus = mem_models.SquareLevel.objects.get(slug='plus')
    class_grad = mem_models.PersonStatus.objects.get(slug='grad')
    join = data['end_date']
    every = mem_models.PersonFrequency.objects.get(slug='every')
    defaults = dict(level=plus, status=class_grad, join_date=join, frequency=every)
    mit_affils = _import_class_get_mit_affils()

    # Process the CSV
    students_text = io.TextIOWrapper(data['student_csv']) # binary mode -> text mode
    reader = csv.DictReader(students_text)
    new_students = []
    for row in reader:
        person, member = _import_class_save_row(row, tsclass, defaults, mit_affils)
        new_students.append((person, member))

    return new_students


@permission_required(['membership.add_tsclass',
                      'membership.add_tsclassmember',
                      'membership.add_person', ])
def import_class(request):
    """View to import members of a class"""
    context = dict(pagename='tsclass')
    if request.method == 'POST':
        form = ImportClassForm(request.POST, request.FILES)
        if form.is_valid():
            # Save
            with reversion.create_revision(atomic=True):
                reversion.set_comment("import class: " + form.cleaned_data['label'])
                reversion.set_user(request.user)
                tsclass = form.save()
                students = _import_class_save_form(form.cleaned_data, tsclass)
                context['tsclass'] = tsclass
                context['students'] = students

    else:
        form = ImportClassForm()
        context['upload_form'] = form

    return render(request, 'membership/import_class.html', context)
