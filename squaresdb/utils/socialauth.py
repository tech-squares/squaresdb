from django.http import HttpResponse
from django.urls import reverse

from social_django.utils import load_strategy, load_backend
from social_core.storage import UserMixin

def saml_metadata_view(request):
    complete_url = reverse('social:complete', args=("saml", ))
    saml_backend = load_backend(
        load_strategy(request),
        "saml",
        redirect_uri=complete_url,
    )
    metadata, errors = saml_backend.generate_metadata_xml()
    if errors:
        return None
    else:
        return HttpResponse(content=metadata, content_type='text/xml')

def clean_saml_username(username):
    # Note that this can be called with email+UUID (and the email might be
    # from Touchstone Collab), which is why don't just trim the end.
    end = '@mit.edu'
    if username.endswith(end):
        username = username[:-len(end)]
    return UserMixin.clean_username(username)
