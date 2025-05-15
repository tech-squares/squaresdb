from distutils.core import setup

setup(
    name = "squaresdb",
    version = "0.1.20240427",
    packages = ["squaresdb"],
    install_requires = [
        # Server
        "django~=5.1",
        "django-reversion",
        "django-select2",
        "pytz", # timezone support TODO: confirm works
        "social-auth-core[saml]>=3.0",
        "social-auth-app-django",
        "django-bootstrap-static>=5,<6"
    ],

    extras_require={
        'scripts': ['flup'], # index.fcgi needs flup
        'mysql': ['mysqlclient'],
        'dev': [
            'pylint', 'pylint-django',  # lint
            'mypy', 'django-stubs',     # type checking
        ],
        'doc': ['sphinx'],
    },

    author = "Tech Squares webapp team",
    author_email = "squares-webapps@mit.edu",
    url = "http://www.mit.edu/~tech-squares/",
    description = 'MIT Tech Squares membership app',
    license = "LICENSE.txt",

    keywords = ["mit", ],
    classifiers = [
        "Programming Language :: Python",
        "Development Status :: 1 - Planning",
        "Environment :: Web Environment",
        "Framework :: Django",
    ],
)
