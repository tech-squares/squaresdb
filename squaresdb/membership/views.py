from django import forms
from django.shortcuts import get_object_or_404, render
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
