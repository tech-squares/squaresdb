from django.conf.urls import url

from squaresdb.gate import views

gate_patterns = [ # pylint:disable=invalid-name
    url(r'^signin/$', views.DanceList.as_view(), name='signin'),
    url(r'^signin/([0-9]+)/$', views.signin, name='signin-dance'),
    url(r'^signin_api/payments$', views.signin_api, name='signin-api'),
    url(r'^signin_api/payment_undo$', views.signin_api_undo, name='signin-api-undo'),
    url(r'^books/([0-9]+)/$', views.books, name='books-dance'),
    url(r'^new_period/$', views.new_sub_period, name='new-period'),
    url(r'^voting/$', views.voting_members, name='voting'),
]

def urls():
    return (gate_patterns, 'gate', 'gate', )
