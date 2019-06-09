import logging

from django.contrib.auth.models import User
from django.test import TestCase

import squaresdb.membership.models as member_models

logger = logging.getLogger(__name__)

# Create your tests here.

def make_person(name):
    level = member_models.SquareLevel.objects.get(slug="?")
    status = member_models.PersonStatus.objects.get(slug="grad")
    mit_affil = member_models.MITAffil.objects.get(slug="none")
    fee_cat = member_models.FeeCategory.objects.get(slug="full")
    freq = member_models.PersonFrequency.objects.get(slug="monthly")
    return member_models.Person.objects.create(
        name=name, email="testing@mit.edu",
        level=level, status=status, mit_affil=mit_affil, fee_cat=fee_cat,
        frequency=freq,
    )

class PersonAuthLinkTestCase(TestCase):
    def setUp(self):
        self.person = make_person("John Doe")

    def test_create(self):
        creator = User.objects.get(username="importer@SYSTEM")
        link = member_models.PersonAuthLink.create_auth_link(
            self.person, reason="testing", detail="testing",
            creator=creator,
        )
        link.save()
        valid, obj = member_models.PersonAuthLink.get_link(link.secret, None)
        self.assertTrue(valid)
        valid, obj = member_models.PersonAuthLink.get_link("asdf", None)
        self.assertFalse(valid)
        self.assertEqual(obj, None)
