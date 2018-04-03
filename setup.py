from distutils.core import setup

setup(
    name = "squaresdb",
    version = "0.1.2018-04-02",
    packages = ["squaresdb"],
    install_requires = [
        # Server
        "django",
        "django-reversion",
        "pytz", # timezone support TODO: confirm works
        "social-auth-core[saml]",
        "social-auth-app-django",
    ],

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
