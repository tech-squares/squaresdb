Installing SquaresDB
====================

Dependencies
------------

Most SquaresDB dependencies will be installed automatically by ``pip``, but some need to be installed already:

- python (2.7)
- xmlsec1 (Debian: ``apt install libxmlsec1-dev``; Fedora: ``xmlsec1-devel``)

Here's a list of some of the key pip-installable dependencies, and what they're
used for:

- ``django``: web framework (`Django docs`_)
- ``django-reversion``: version controlling objects in the DB (`reversion
  docs`_)
- ``social-auth-core`` and ``social-auth-app-django``: support for
  authenticating with Google and MIT Touchstone (`social-auth docs`_)
- ``python-saml``: ``social-auth`` dependency for MIT Touchstone, which is
  SAML-based (`python-saml docs`_ -- these are the most recent I've found,
  though there seem to be older versions various places)

.. _Django docs: https://docs.djangoproject.com/en/
.. _reversion docs: http://django-reversion.readthedocs.io/en/stable/
.. _social-auth docs: https://python-social-auth.readthedocs.io/en/latest/
.. _python-saml docs: http://pythonhosted.org/python-saml/#

Local install
-------------

The DB is pip-installable, so on a Linux machine, at least, you should be 
able to get it running with::

  VENV=venv-name
  virtualenv $VENV
  . $VENV/bin/activate
  pip install --upgrade pip # often optional; required on some older systems (like scripts.mit.edu)
  pip install -e git+https://github.com/tech-squares/squaresdb.git#egg=squaresdb
  cd $VENV/src/squaresdb/squaresdb/
  utils/install.py --email whatever

See also https://diswww.mit.edu/pergamon/squares-webapps/21 (requires MIT certs).

Installing on Scripts
---------------------

Much the same instructions should work. There's some tweaks -- the summary is::

  VENV=venv-name
  virtualenv $VENV
  . $VENV/bin/activate
  pip install --upgrade pip # often optional; required on some older systems (like scripts.mit.edu)
  CFLAGS=-DXMLSEC_NO_SIZE_T pip install -e git+https://github.com/tech-squares/squaresdb.git@socialauth#egg=squaresdb[scripts]
  cd $VENV/src/squaresdb/squaresdb/
  utils/install.py --email whatever --scripts

In more depth: Fedora's ``xmlsec1`` packaging or something seems to be buggy,
so `you should`_ run ``pip install`` with ``CFLAGS=-DXMLSEC_NO_SIZE_T``. You
can just prepend that to the ``squaresdb`` install line, or if you don't,
uninstall and reinstall ``dm.xmlsec.binding``::

  pip uninstall dm.xmlsec.binding
  CFLAGS=-DXMLSEC_NO_SIZE_T pip install --no-cache-dir dm.xmlsec.binding

.. _you should: https://github.com/onelogin/python-saml/issues/30#issuecomment-329553833

The ``--scripts`` option will make the installer do various scripts-specific
things:

- configure ``DATABASES`` to use sql.mit.edu (not sqlite), and creates the database
- configure ``ALLOWED_HOSTS`` to include tech-squares.mit.edu,
  locker.scripts.mit.edu, and s-a.mit.edu (a specific scripts host, useful for
  using ``manage.py runserver``)
- configure admin media to use shared scripts copies as applicable
- configure various other settings
- create the directory in ``web_scripts``, with appropriate FastCGI and `.htaccess`` config


Configuring Google and MIT auth
-------------------------------

SquaresDB supports using python-social-auth_ to authenticate using Google and
MIT Shibboleth.

.. _python-social-auth: https://python-social-auth.readthedocs.io/en/latest/index.html

Google auth
^^^^^^^^^^^

To use Google auth, go to the `Google APIs Dashboard`_. Choose "Credentials" in
the left sidebar, and then "Create credentials" -> "OAuth client ID".
"Application type" can be web application and name can be whatever you like.
"Authorized JavaScript origins" is just the origin -- for my local dev server,
I use ``http://localhost:8007``. "Authorized redirect URIs" should be the base
URL for your DB install, plus ``/sauth/complete/google-oauth2/`` -- for dev, I
use ``http://localhost:8007/sauth/complete/google-oauth2/``.

You should then copy the "Client ID" into ``local.py`` as the
``SOCIAL_AUTH_GOOGLE_OAUTH2_KEY``, and the "Client secret" in as
``SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET``.

In addition, you will need to enable the `Google+ API`_.

.. _Google APIs Dashboard: https://console.developers.google.com/apis/dashboard
.. _Google+ API: https://console.developers.google.com/apis/library/plus.googleapis.com/

MIT or other Shibboleth auth
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

MIT Touchstone authentication is based on the Shibboleth project, which itself uses SAML. We mostly preconfigure ``python-social-auth``'s SAML support. The main thing individual installs need to do are to set up certificates and provide metadata to the IdP.

To create a certificate, run::
    openssl req -new -x509 -days 3652 -nodes -out saml.crt -keyout saml.key

while in the ``settings`` directory. The default settings will automatically
read those files if they exist.

Setting up IdP metadata is slightly more involved. Once you have created the
certificates above, load http://localhost:8007/saml_metadata/ (or the
equivalent on your server) and save it somewhere convenient. If there's an
element ``<md:KeyDescriptor use="signing">``, delete the ``use="signing"``
(leaving just ``<md:KeyDescriptor>``). I'm not clear on why the library
degenerates this apparently-incorrect metadata, but it seems to, and without
deleting the ``use="signing"`` snippet can cause errors like ``Unable to
encrypt assertion``.

The simplest way to test Shibboleth auth is with the TestShib_ provider, which
allows self-service setup. Enabling TestShib is controlled by the
``ENABLE_TESTSHIB`` setting, or if not defined by the ``DEBUG`` setting -- in
general, without tweaking ``ENABLE_TESTSHIB`` or any other auth-related Django
setting, dev servers with SAML certs will automatically try to use TestShib,
but production will not. However, you will need to upload the metadata to
TestShib. To do so, make sure your metadata file is named something unique (but
whose name you won't forget), visit https://www.testshib.org/register.html, and
upload the metadata file. The upload confirmation page will give you
configuration instructions, which you can ignore (since TestShib should be
pre-configured), and test instructions, which may have useful debugging links.
To test, though, you'll want to visit
http://localhost:8007/sauth/login/saml/?idp=testshib or equivalent. If all goes
well, it will redirect you to a TestShib page that lists some passwords, and
once you enter one and ignore any encryption warnings, you'll be dumped back at
http://localhost:8007/accounts/profile/ or equivalent, which will likely 404
for now. However, if you go back to the homepage, you should be logged in.

.. _TestShib: https://www.testshib.org/

For MIT, `IS&T provides docs`_ on registering with their IdP in the section
"Letting the IdP know about your application". You'll need to send them various
pieces of information.

.. _IS&T provides docs: https://wikis.mit.edu/confluence/display/TOUCHSTONE/Provisioning+Steps
