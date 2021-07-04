from django.conf.urls import url

from squaresdb.gate import views

gate_patterns = [ # pylint:disable=invalid-name
    url(r'^signin/$', views.DanceList.as_view(), name='signin'),
    url(r'^signin/([0-9]+)/$', views.signin, name='signin-dance'),
    url(r'^signin_api/payments$', views.signin_api, name='signin-api'),
    url(r'^books/([0-9]+)/$', views.books, name='books-dance'),
]

def urls():
    return (gate_patterns, 'gate', 'gate', )
