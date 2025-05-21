import logging

from django.test import Client, TestCase
from django.urls import reverse

logger = logging.getLogger(__name__)

class PayTestCase(TestCase):
    fixtures = ['people.json', 'sample.json', 'squares.json', ]

    def test_start(self):
        client = Client()
        path = reverse('pay:start')
        with self.assertNumQueries(2):
            response = client.get(path)
        logger.info(response)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Squares Pay")
        self.assertContains(response, "Rounds class")
        self.assertContains(response, "Pay what you think is right for you")
