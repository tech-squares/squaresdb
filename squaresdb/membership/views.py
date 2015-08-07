from django.shortcuts import get_object_or_404, render

import squaresdb.membership.models

def view_person(request, pk):
    person = get_object_or_404(squaresdb.membership.models.Person, pk=pk)
    return render(request, 'membership/person_detail.html', dict(person=person))
