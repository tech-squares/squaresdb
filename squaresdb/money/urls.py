from django.urls import path

from squaresdb.money import views

pay_patterns = [
    path('', views.pay_start, name='start'),
    path('history/', views.PayHistoryList.as_view(), name='history', ),
    path('receipt/<int:pk>/', views.pay_receipt, name='receipt-user'),
    path('post/cybersource/<int:pk>/<slug:nonce>/', views.pay_post_cybersource,
         name='post-cybersource'),
    path('receipt/<int:pk>/<slug:nonce>/', views.pay_receipt,
         name='receipt'),
    path('error/cybersource/', views.pay_error_cybersource,
         name='error-cybersource'),
    path('mock/cybersource/', views.pay_mock_cybersource,
         name='mock-cybersource', ),
]
pay_urls = (pay_patterns, 'money')
