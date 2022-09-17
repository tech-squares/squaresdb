import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.test import TestCase
from django.urls import reverse

import squaresdb.gate.models as gate_models

logger = logging.getLogger(__name__)

def get_user(perm):
    user = get_user_model().objects.create_user(username='user', password='pass')
    content_type = ContentType.objects.get_for_model(gate_models.Attendee)
    permission = Permission.objects.get(content_type=content_type, codename=perm)
    user.user_permissions.add(permission)
    user.save()
    return user

class SigninTestCase(TestCase):
    fixtures = ['people.json', 'sample.json']

    def setUp(self):
        self.user = get_user('signin_app')

    def test_render_index(self):
        client = Client()
        client.force_login(self.user)
        path = reverse('gate:index')
        with self.assertNumQueries(7):
            response = client.get(path)
        logger.info(response)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Current Dances")

    def test_render_sub_period(self):
        client = Client()
        client.force_login(self.user)
        path = reverse('gate:sub-period', args=('2019-spring',))
        with self.assertNumQueries(7):
            response = client.get(path)
        logger.info(response)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Spring 2019")

    def test_render_dance(self):
        client = Client()
        client.force_login(self.user)
        path = reverse('gate:signin-dance', args=(2,))
        with self.assertNumQueries(17):
            response = client.get(path)
        logger.info(response)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Squares Signin for ")

class BooksTestCase(TestCase):
    fixtures = ['people.json', 'sample.json']

    def setUp(self):
        self.user = get_user('books_app')

    def test_render_books(self):
        client = Client()
        client.force_login(self.user)
        path = reverse('gate:books-dance', args=(2,))
        with self.assertNumQueries(16):
            response = client.get(path)
        logger.info(response)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Payments")
