"""squaresdb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import TemplateView

import squaresdb.gate.urls
import squaresdb.membership.urls
import squaresdb.utils.socialauth

urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html',
                                  extra_context={'pagename':'homepage'}),
         name='homepage'),
    path('admin/', admin.site.urls),
    path("select2/", include("django_select2.urls")),
    path('membership/', squaresdb.membership.urls.urls()),
    path('gate/', squaresdb.gate.urls.urls()),
    path('accounts/', include('django.contrib.auth.urls')),
    path('sp', TemplateView.as_view(template_name='sp.html'),
        name='saml-sp'),
    path('sauth/', include('social_django.urls', namespace='social')),
    path('saml_metadata/', squaresdb.utils.socialauth.saml_metadata_view),
]
