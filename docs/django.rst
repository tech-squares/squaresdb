Django features
===============

SquaresDB is based on the Django web framework, which has a variety of features. Notes about features we should consider using in the future are scattered throughout the code (for example as ``TODO(django-3.2)`` and in the bugtracker, but also sometimes below.

Features that may be useful
---------------------------
* `Async support <https://docs.djangoproject.com/en/dev/topics/async/>`_ -- realistically, we're probably not perf sensitive enough to care (plus our blocking IO is all(?) DB access, and the ORM is still sync-only), but it's neat
* The admin `display <https://docs.djangoproject.com/en/dev/ref/contrib/admin/#django.contrib.admin.display>`_ decorator might simplify a nice-looking admin
* It looks like maybe Python now has `builtin timezone info <https://docs.djangoproject.com/en/dev/releases/3.2/#miscellaneous>`_?

Deprecation
-----------

* ``staticfiles`` was deprecated in 2.1 (`static <https://docs.djangoproject.com/en/dev/releases/2.1/#features-deprecated-in-2-1>`_ is a straightforward replacement, apparently)
* Django seems to be moving away from `whitelist <https://docs.djangoproject.com/en/dev/releases/3.2/#id3>`_
