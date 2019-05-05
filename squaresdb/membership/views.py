import logging

from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.core import mail
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from social_django.models import UserSocialAuth

import squaresdb.membership.models

logger = logging.getLogger(__name__)


@permission_required('membership.view_person')
def view_person(request, pk):
    person = get_object_or_404(squaresdb.membership.models.Person, pk=pk)
    return render(request, 'membership/person_detail.html', dict(person=person))


def format_date(date):
    if date: return date.strftime("%B %d, %Y")
    else: return "unknown"


def email_context_dict(person):
    data = {}
    for field in 'name email'.split(' '):
        data['person_'+field] = getattr(person, field)
    data['person_level'] = person.level.name
    data['person_member_status'] = person.status.full_str()
    data['person_join_date'] = format_date(person.join_date)
    data['person_mit_affil'] = person.mit_affil.full_str()
    data['person_grad_year'] = person.grad_year or "unknown or N/A"
    data['person_fee_cat'] = person.fee_cat
    return data


class PersonForm(forms.ModelForm):
    mark_correct = forms.BooleanField(required=False, help_text="If your information is correct, please check this box so we know how recent the information is.")

    class Meta:
        model = squaresdb.membership.models.Person
        fields = ['name', 'email', 'level']

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


# TODO: warn when changing email
# TODO: allow self-service creation of links
# TODO: mail-merged links should expire after more time (probably)
# TODO: deployment story (given scripts.mit.edu doesn't support Py3.5+ now)


UPDATE_EMAIL_TEMPLATE = """
Hi %(person_name)s,

Thank you for updating your entry in the Tech Squares Membership Database. Your new information is:
Name:               %(person_name)s
Email:              %(person_email)s
Highest level:      %(person_level)s
Membership status:  %(person_member_status)s
Member since:       %(person_join_date)s
MIT affiliation:    %(person_mit_affil)s
MIT grad year:      %(person_grad_year)s
Fee category:       %(person_fee_cat)s

Thanks,
Tech Squares
"""

def edit_person_obj(request, person):
    """Helper to edit a Person

    The user calling the function is assumed to have permission to edit the
    Person passed -- callers are responsible for identifying the correct
    Person and checking authz.
    """
    msg = None
    initial = {}
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
            email_body = UPDATE_EMAIL_TEMPLATE % email_context_dict(request_obj)
            email = mail.EmailMessage(subject="Tech Squares MemberDB update",
                body=email_body, to=set([request_obj.email, old_email]),
            )
            mail.get_connection().send_messages([email])

            # Actually save the object
            request_obj.save()
            form.save_m2m()
            msg = "Thanks for editing!"
        else:
            msg = "Validation failed. See below for details."
    else:
        form = PersonForm(instance=person, initial=initial, ) # An unbound form
    context = dict(
        person=person,
        form=form,
        msg=msg,
        pagename='person-edit',
    )
    return render(request, 'membership/person_self_edit.html', context)


@login_required
def edit_user_person(request, person_id=None):
    """Edit a Person corresponding to the logged-in user
    """
    emails = [request.user.email]

    # TODO: extract email addresses from social accounts, not just Django user
    # record?
    social = UserSocialAuth.get_social_auth_for_user(request.user)
    logger.info("social=%s", social)
    if len(social) > 0:
        logger.info("social[0]=%s", social[0].__dict__)

    # Find the people record
    people = squaresdb.membership.models.Person.objects.filter(email__in=emails)
    if person_id:
        people = people.filter(pk=person_id)

    # Edit the people record
    if len(people) == 1:
        person = people[0]
        return edit_person_obj(request, person)
    elif len(people) > 1:
        context = {
            'pagename':'person-edit',
            'people':people,
        }
        return render(request, 'membership/PersonUser/choose.html', context)
    elif len(people) == 0:
        # TODO: unknown page
        return render(request, 'membership/PersonUser/unknown.html')


PERSONAUTHLINK_RESEND_TEMPLATE = """Hi %(person_name)s,

Your requested link for editing your Tech Squares Membership DB entry is:

    %(link)s

If you did not request this, please let us know at squares-db-request@mit.edu.

Thanks,
Tech Squares
"""

def resend_personauthlink(request, old_link):
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
    data['link'] = request.build_absolute_uri(reverse('membership:person-link', args=[new_link.secret]))
    msg_body = PERSONAUTHLINK_RESEND_TEMPLATE % data
    msg = mail.EmailMessage(subject="New link to update Tech Squares Membership DB",
        body=msg_body, to=[new_link.person.email]
    )
    connection = mail.get_connection()
    connection.send_messages([msg])


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
    # Ideally, we'd use a Django template, but the security story there seems
    # dubious.
    default_template = """Hi %(person_name)s,

The Tech Squares Membership DB is moving online. You can update (much of) your information at:

    %(link)s

That page will also let you tell us that your information is correct -- until you do, we may continue to follow up with you, so we appreciate you visiting the page, even if your information is right already.

Your current information is:
Name:           %(person_name)s
Email:          %(person_email)s
Highest level:  %(person_level)s

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
    subject = forms.CharField(initial='Tech Squares Membership Database')
    template = forms.CharField(initial=default_template, widget=forms.Textarea)
    people_qs = squaresdb.membership.models.Person.objects.all()
    people = forms.ModelMultipleChoiceField(queryset=people_qs)

    def __init__(self, *args, **kwargs):
        super(BulkPersonAuthLinkCreationForm, self).__init__(*args, **kwargs)
        self.fields['reason'].widget.attrs['size'] = 80
        self.fields['subject'].widget.attrs['size'] = 80
        self.fields['template'].widget.attrs['rows'] = 20
        self.fields['template'].widget.attrs['cols'] = 80

    def format_template(self, request, person, link):
        data = email_context_dict(person)
        data['link'] = request.build_absolute_uri(reverse('membership:person-link', args=[link.secret]))
        return self.cleaned_data['template'] % data

    def send_emails(self, request):
        msgs = []
        for person in self.cleaned_data['people']:
            link = squaresdb.membership.models.PersonAuthLink.create_auth_link(
                person, reason='BulkPersonAuthLinkCreation',
                detail=self.cleaned_data['reason'], creator=request.user,
            )
            link.create_ip = request.META['REMOTE_ADDR']
            link.save()
            msg = self.format_template(request, person, link)
            msgs.append(mail.EmailMessage(subject=self.cleaned_data['subject'],
                body=msg, to=[person.email]
            ))
        connection = mail.get_connection()
        connection.send_messages(msgs)


@permission_required('membership.bulk_create_personauthlink')
def create_personauthlinks(request):
    msg = ''
    if request.method == 'POST': # If the form has been submitted...
        form = BulkPersonAuthLinkCreationForm(
            request.POST,
        )

        if form.is_valid(): # All validation rules pass
            form.send_emails(request)
            msg = "Created %d PersonAuthLink objects" % (len(form.cleaned_data['people']), )
    else:
        initial = {}
        if 'people' in request.GET:
            people = request.GET['people'].split(',')
            initial['people'] = people
        form = BulkPersonAuthLinkCreationForm(initial=initial) # An unbound form
    context = dict(
        form=form,
        msg=msg,
        pagename='personauthlink-bulkcreate',
    )
    return render(request, 'membership/personauthlink_bulkcreate.html', context)
