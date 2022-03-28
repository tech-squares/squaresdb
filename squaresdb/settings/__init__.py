"""
Django settings for squaresdb project.

Generated by 'django-admin startproject' using Django 1.8.1.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

from typing import List

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Use local version of JS and CSS libs (for offline dev), or from CDN
#USE_LOCAL_LIBS = True
#USE_LOCAL_LIBS = False
# TODO: Actually support a local vs remote JS/CSS libs setting
# https://stackoverflow.com/questions/433162/can-i-access-constants-in-settings-py-from-templates-in-django
# is likely to be useful, but they seem messy enough I'm punting for now.

ALLOWED_HOSTS = [] # type: List[str]

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True

# EMAIL SETTINGS

DEFAULT_FROM_EMAIL = 'Squares DB <squares-db@mit.edu>'

# Error emails
EMAIL_SUBJECT_PREFIX = '[SquaresDB] '
SERVER_EMAIL = 'squares-db-auto@mit.edu'
ADMINS = [
    ('Squares DB Errors', 'squares-db-errorlog@mit.edu')
]
MANAGERS = ADMINS

# ForcedRecipientEmailBackend sends all email to EMAIL_FORCED_RECIPIENTS,
# rather than the specified recipient. It's useful for testing. Such emails
# are labeled by adding a fake recipient to the "To" header. The label can be
# left the same between dev installs, and an option is defined here:
EMAIL_FORCED_RECIPIENTS_LABEL = "squares-db-forced-recipient@mit.edu"

# AutoBccEmailBackend BCCs specified addresses on all outgoing emails, and is
# intended for production use. We expect to use the following for all prod
# deployments:
EMAIL_AUTO_BCC = ["squares-db-outgoing@mit.edu"]

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'reversion',
    'social_django',
    'squaresdb.membership',
    'squaresdb.gate',
)

MIDDLEWARE = (
    'reversion.middleware.RevisionMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

AUTHENTICATION_BACKENDS = (
    #'social_core.backends.open_id.OpenIdAuth',
    #'social_core.backends.google.GoogleOpenId',
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.saml.SAMLAuth',
    #'social_core.backends.google.GoogleOAuth',
    #'social_core.backends.twitter.TwitterOAuth',
    #'social_core.backends.yahoo.YahooOpenId',
    'django.contrib.auth.backends.ModelBackend',
)

ENABLE_TESTSHIB = None # enable if DEBUG=True

SITE_WEB_PATH = "/"

LOGIN_REDIRECT_URL = 'homepage' # named URL pattern

ROOT_URLCONF = 'squaresdb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'squaresdb', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'squaresdb.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/New_York'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

from .local import * # pylint: disable=wrong-import-position

settings_dir = os.path.dirname(os.path.abspath(__file__)) # pylint:disable=invalid-name

def read_settings_file(filename):
    """Read a file from the settings dir and return the contents"""
    # The encoding really shouldn't matter here (these should all be
    # 7-bit ASCII), but UTF-8 is fine.
    with open(os.path.join(settings_dir, filename), encoding='utf-8') as file_obj:
        return file_obj.read()

if os.path.isfile(os.path.join(settings_dir, "saml.key")):
    # InCommon has some opinions on what Entity IDs should look like:
    # https://spaces.at.internet2.edu/display/federation/saml-metadata-entityid
    SOCIAL_AUTH_SAML_SP_ENTITY_ID = SITE_SERVER+SITE_WEB_PATH+'sp'

    SOCIAL_AUTH_SAML_SP_PUBLIC_CERT = read_settings_file('saml.crt')
    SOCIAL_AUTH_SAML_SP_PRIVATE_KEY = read_settings_file('saml.key')
    SOCIAL_AUTH_SAML_ORG_INFO = {
        "en-US": {
            "name": "techsquares",
            "displayname": "MIT Tech Squares",
            "url": "http://tech-squares.mit.edu/"
        }
    }
    SOCIAL_AUTH_SAML_TECHNICAL_CONTACT = {
        "givenName": "Tech Squares",
        "emailAddress": "squares-saml@mit.edu"
    }
    SOCIAL_AUTH_SAML_SUPPORT_CONTACT = {
        "givenName": "Tech Squares",
        "emailAddress": "squares-saml@mit.edu"
    }

    SOCIAL_AUTH_SAML_ENABLED_IDPS = {}

    if ENABLE_TESTSHIB is None:
        ENABLE_TESTSHIB = DEBUG

    if ENABLE_TESTSHIB:
        SOCIAL_AUTH_SAML_ENABLED_IDPS["testshib"] = {
            "entity_id": "https://samltest.id/saml/idp",
            "url": "https://samltest.id/idp/profile/SAML2/Redirect/SSO",
            # https://samltest.id/download/ after uploading my data
            "x509cert": read_settings_file('samltest.crt'),
        }

    SOCIAL_AUTH_SAML_ENABLED_IDPS["mit"] = {
        "entity_id": "https://idp.mit.edu/shibboleth",
        "url": "https://idp.mit.edu/idp/profile/SAML2/Redirect/SSO",
        # From http://web.mit.edu/touchstone/shibboleth/config/metadata/MIT-metadata.xml,
        # under "<!-- MIT's core IdP. -->"
        "x509cert": read_settings_file('mitshib.crt'),
        # MIT doesn't seem to provide the "urn:oid:0.9.2342.19200300.100.1.1"
        # (OID_USERID, per social_core.backends.saml) attribute, but does
        # provide this one (OID_MAIL), so use it instead.
        # Sample response:
        # 'urn:oid:0.9.2342.19200300.100.1.3': ['adehnert@mit.edu'],
        # 'urn:oid:1.3.6.1.4.1.5923.1.1.1.1': ['affiliate'],
        # 'urn:oid:1.3.6.1.4.1.5923.1.1.1.2': ['Alexander W Dehnert'],
        # 'urn:oid:1.3.6.1.4.1.5923.1.1.1.5': ['affiliate'],
        # 'urn:oid:1.3.6.1.4.1.5923.1.1.1.6': ['adehnert@mit.edu'],
        # 'urn:oid:1.3.6.1.4.1.5923.1.1.1.9': ['affiliate@mit.edu'],
        # 'urn:oid:2.16.840.1.113730.3.1.241': ['Alex Dehnert'],
        "attr_user_permanent_id": "urn:oid:0.9.2342.19200300.100.1.3",
    }

    SOCIAL_AUTH_SAML_ENABLED_IDPS["tscollab"] = {
        "entity_id": "https://idp.touchstonenetwork.net/shibboleth-idp",
        "url": "https://idp.touchstonenetwork.net/idp/profile/SAML2/Redirect/SSO",
        # From http://web.mit.edu/touchstone/shibboleth/config/metadata/MIT-metadata.xml,
        # under "<!-- idp.touchstonenetwork.net, CAMS IdP. -->"
        "x509cert": read_settings_file('tscollab.crt'),
        # Again, Touchstone Collaboration accounts don't seem to bother with a
        # userid, so we override it again, with the same value as for MIT.
        # Sample response:
        # 'urn:oid:2.5.4.42': ['Alex'],
        # 'urn:oid:2.5.4.4': ['Dehnert'],
        # 'urn:oid:2.16.840.1.113730.3.1.241': ['Alex Dehnert'],
        # 'urn:oid:1.3.6.1.4.1.5923.1.1.1.6': ['alex.dehnert_1@touchstonenetwork.net'],
        # 'urn:oid:0.9.2342.19200300.100.1.3': ['alex.dehnert@gmail.com']
        "attr_user_permanent_id": "urn:oid:0.9.2342.19200300.100.1.3",
    }

    SOCIAL_AUTH_SAML_SECURITY_CONFIG = {
        # By default, python-saml seems to use
        # urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport
        # which causes MIT's IdP to only allow passwords, not certs or
        # Kerberos. Setting it to false causes python-saml to leave out the
        # <samlp:RequestedAuthnContext> entirely, which works better.
        'requestedAuthnContext': False,
        'wantAssertionsEncrypted': True,
    }
