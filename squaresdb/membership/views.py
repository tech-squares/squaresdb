from django.shortcuts import get_object_or_404, render

import squaresdb.membership.models

def view_person(request, pk):
    person = get_object_or_404(squaresdb.membership.models.Person, pk=pk)
    return render(request, 'membership/person_detail.html', dict(person=person))


def edit_person_personauthlink(request, secret):
    request_ip = request.META['REMOTE_ADDR']
    valid, link = squaresdb.membership.models.PersonAuthLink.get_link(secret, request_ip)
    if valid:
        return render(request, 'membership/person_detail.html', dict(person=link.person))
    else:
        if link:
            return render(request, 'membership/PersonAuthLink/invalid.html')
        else:
            return render(request, 'membership/PersonAuthLink/unknown.html')
