from distutils.core import setup

setup(
    name = "squaresdb",
    version = "0.1.2020-03-01",
    packages = ["squaresdb"],
    install_requires = [
        # Server
        "django",
        "django-reversion",
        "pytz", # timezone support TODO: confirm works
        "social-auth-core[saml]>=3.0",
        "social-auth-app-django",
    ],

    extras_require={
        'scripts': ['flup'], # index.fcgi needs flup
        'mysql': ['mysqlclient'],
        'dev': [
            'pylint', 'pylint-django',  # lint
            'mypy', #'django-stubs',     # type checking
            # Pin django-stubs until 1.9 (with Django 3.2) releases
            'django-stubs @ git+https://github.com/typeddjango/django-stubs.git@8c387e85fe5d3c3759b4ecbba643b0f2491fd063',
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
