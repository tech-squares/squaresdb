from django.conf.urls import url

import squaresdb.gate.views as views

gate_patterns = [ # pylint:disable=invalid-name
    url(r'^signin/([0-9a-z-]+)/$', views.signin, name='signin'),
    url(r'^signin_api/payments$', views.signin_api, name='signin-api'),
]

def urls():
    return (gate_patterns, 'gate', 'gate', )
