from django.urls import path

from squaresdb.membership import views

membership_patterns = [ # pylint:disable=invalid-name
    path('person/<int:pk>/', views.view_person, name='person'),
    path('person/edit/', views.edit_user_person, name='person-user-edit'),
    path('person/edit/<int:pk>/', views.edit_user_person, name='person-user-edit-id'),
    path('person/link/<slug:secret>/', views.edit_person_personauthlink, name='person-link'),
    path('link/bulk_create/', views.create_personauthlinks, name='personauthlink-bulkcreate'),
    path('class/', views.ClassList.as_view(), name='class-list'),
    path(r'class/<int:pk>/', views.ClassDetail.as_view(), name='class-detail'),
    path('class/import/', views.import_class, name='class-import'),
]

def urls():
    return (membership_patterns, 'membership', 'membership', )
