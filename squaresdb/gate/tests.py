import logging

from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.test import TestCase
from django.urls import reverse

import squaresdb.gate.models as gate_models

logger = logging.getLogger(__name__)

class SigninTestCase(TestCase):
    fixtures = ['people.json', 'sample.json']

    def setUp(self):
        self.user = User.objects.create_user(username='user', password='pass')
        content_type = ContentType.objects.get_for_model(gate_models.Attendee)
        permission = Permission.objects.get(content_type=content_type, codename='signin_app')
        self.user.user_permissions.add(permission)
        self.user.save()

    def test_render(self):
        client = Client()
        client.force_login(self.user)
        path = reverse('gate:signin', args=('2019-summer',))
        with self.assertNumQueries(10):
            response = client.get(path)
        logger.info(response)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Squares Signin for ")