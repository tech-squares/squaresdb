from django.urls import path

from squaresdb.gate import views

gate_patterns = [ # pylint:disable=invalid-name
    path('', views.index, name='index'),
    path('period/<slug:slug>/', views.SubPeriodView.as_view(), name='sub-period'),
    path('period/<slug:slug>/bulk_sub/', views.bulk_sub, name='bulk-sub'),
    path('period/<slug:slug>/member_stats/', views.member_stats, name='member-stats'),
    path('signin/<int:pk>/', views.signin, name='signin-dance'),
    path('signin_api/payments', views.signin_api, name='signin-api'),
    path('signin_api/payment_undo', views.signin_api_undo, name='signin-api-undo'),
    path('books/<int:pk>/', views.books, name='books-dance'),
    path('new_period/', views.new_sub_period, name='new-period'),
    path('sub_upload/', views.upload_subs, name='sub-upload'),
    path('voting/', views.voting_members, name='voting'),
    path('paper-gate/', views.paper_gate, name='paper-gate'),
]

def urls():
    return (gate_patterns, 'gate', 'gate', )
