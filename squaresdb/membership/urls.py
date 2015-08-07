from django.conf.urls import include, url

import squaresdb.membership.views as views

membership_patterns = [
    url(r'^person/(\d+)/$', views.view_person, name='person'),
]

def urls():
    return (membership_patterns , 'membership', 'membership', )
