from django import forms
from django.contrib.auth.decorators import permission_required
from django.core import mail
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

import squaresdb.membership.models

def view_person(request, pk):
    person = get_object_or_404(squaresdb.membership.models.Person, pk=pk)
    return render(request, 'membership/person_detail.html', dict(person=person))


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


def edit_person_personauthlink(request, secret):
    request_ip = request.META['REMOTE_ADDR']
    valid, link = squaresdb.membership.models.PersonAuthLink.get_link(secret, request_ip)
    if valid:
        msg = None
        initial = {}
        if request.method == 'POST': # If the form has been submitted...
            # A form bound to the POST data
            form = PersonForm(
                request.POST, request.FILES,
                instance=link.person,
            )

            if form.is_valid(): # All validation rules pass
                request_obj = form.save(commit=False)
                if form.cleaned_data['mark_correct']:
                    request_obj.last_marked_correct = timezone.now()
                request_obj.save()
                form.save_m2m()
                msg = "Thanks for editing!"
            else:
                msg = "Validation failed. See below for details."
        else:
            form = PersonForm(instance=link.person, initial=initial, ) # An unbound form
        context = dict(
            person=link.person,
            form=form,
            msg=msg,
            pagename='person-edit',
        )
        return render(request, 'membership/person_self_edit.html', context)
    else:
        if link:
            return render(request, 'membership/PersonAuthLink/invalid.html')
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
Name:   %(person_name)s
Email:  %(person_email)s
Level:  %(person_level)s

To update the following information, please email squares-db-request@mit.edu:
[[some stuff]]

Thanks,
Tech Squares
"""

    reason = forms.CharField()
    subject = forms.CharField(initial='Tech Squares Membership Database')
    template = forms.CharField(initial=default_template, widget=forms.Textarea)
    people_qs = squaresdb.membership.models.Person.objects.all()
    people = forms.ModelMultipleChoiceField(queryset=people_qs)

    def format_template(self, request, person, link):
        data = {}
        data['link'] = request.build_absolute_uri(reverse('membership:person-link', args=[link.secret]))
        for field in 'name email'.split(' '):
            data['person_'+field] = getattr(person, field)
        data['person_level'] = person.level.name
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
        form = BulkPersonAuthLinkCreationForm(initial=initial) # An unbound form
    context = dict(
        form=form,
        msg=msg,
        pagename='personauthlink-bulkcreate',
    )
    return render(request, 'membership/personauthlink_bulkcreate.html', context)
