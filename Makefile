all : test

.PHONY: all test mypy pylint django-check django-test

test: django-check django-test mypy pylint tscheck

django-check:
	python manage.py check

django-test:
	python manage.py test

mypy:
	# incremental mypy is broken with Django?
	# https://github.com/typeddjango/django-stubs/issues/760
	mypy --version && mypy --no-incremental -p squaresdb

pylint:
	pylint --version && pylint --rcfile=pylintrc.ini squaresdb/

tscheck:
	npm run tscheck

runserver:
	python manage.py runserver 8007
