from distutils.core import setup

setup(
    name = "squaresdb",
    version = "0.1.2020-02-29",
    packages = ["squaresdb"],
    install_requires = [
        # Server
        "django",
        "django-reversion",
        "pytz", # timezone support TODO: confirm works
        "social-auth-core[saml]",
        "social-auth-app-django",
    ],

    extras_require={
        'scripts': ['flup'], # index.fcgi needs flup
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
