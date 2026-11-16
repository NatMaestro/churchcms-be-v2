"""
The API documentation (/api/docs/, /api/redoc/, /api/schema/) lists every
endpoint, so only platform superadmins may open it. Church admins, members
and visitors are refused.
"""
from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient

from apps.authentication.models import User

DOC_URLS = ('/api/schema/', '/api/docs/', '/api/redoc/')


class ApiDocsAccessTests(TestCase):
    def setUp(self):
        connection.set_schema_to_public()
        self.superadmin = User.objects.create_user(email='owner@platform.example.test', password='pass-12345',
                                                   name='Platform Owner', role='superadmin')
        self.church_admin = User.objects.create_user(email='admin@church.example.test', password='pass-12345',
                                                     name='Church Admin', role='admin')

    def test_visitors_cannot_open_the_api_docs(self):
        for url in DOC_URLS:
            self.assertIn(APIClient().get(url).status_code, (401, 403), url)

    def test_church_admins_cannot_open_the_api_docs(self):
        client = APIClient()
        client.force_authenticate(user=self.church_admin)

        for url in DOC_URLS:
            self.assertEqual(client.get(url).status_code, 403, url)

    def test_platform_superadmins_can_open_the_api_docs(self):
        client = APIClient()
        client.force_authenticate(user=self.superadmin)

        for url in DOC_URLS:
            self.assertEqual(client.get(url).status_code, 200, url)
