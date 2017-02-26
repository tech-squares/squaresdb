import os

# SECURITY WARNING: keep the secret key used in production secret!
#SECRET_KEY = something

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

EMAIL_BACKEND = 'squaresdb.utils.email.ForcedRecipientEmailBackend'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'squaresdb': {
            'handlers': ['console'],
            'level': os.getenv('SQUARESDB_LOG_LEVEL', 'INFO'),
        },
    },
}
