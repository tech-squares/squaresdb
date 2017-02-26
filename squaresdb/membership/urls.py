from django.conf.urls import include, url

import squaresdb.membership.views as views

membership_patterns = [
    url(r'^person/(\d+)/$', views.view_person, name='person'),
    url(r'^person/link/([A-Za-z0-9]+)/$', views.edit_person_personauthlink, name='person-link'),
    url(r'^link/bulk_create/', views.create_personauthlinks, name='personauthlink-bulkcreate'),
]

def urls():
    return (membership_patterns , 'membership', 'membership', )
