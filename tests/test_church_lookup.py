"""
The church lookup by subdomain needs no login, so it must return only the
church's public profile, never its settings, subscription or schema details.
"""
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from apps.churches.models import Church

LOOKUP_URL = '/api/v1/churches/by_subdomain/'
TEST_SCHEMA = 'lookupa'
PUBLIC_FIELDS = {'name', 'subdomain', 'denomination', 'address', 'phone', 'email', 'website'}


class ChurchLookupTests(TransactionTestCase):
    # See tests/test_tenant_binding.py: makes the flush use TRUNCATE ... CASCADE.
    available_apps = list(settings.INSTALLED_APPS)

    def setUp(self):
        cache.clear()  # throttle history lives in the cache
        connection.set_schema_to_public()
        self.church = Church.objects.create(
            schema_name=TEST_SCHEMA, subdomain=TEST_SCHEMA, name='Lookup Parish',
            email='office@lookup.example.test', bypass_subscription_check=True,
            payment_settings={'secret_key': 'sk_test_should_never_leak'},
            integration_settings={'api_key': 'should-never-leak'},
        )

    def tearDown(self):
        cache.clear()
        connection.set_schema_to_public()
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{TEST_SCHEMA}" CASCADE')

    def test_lookup_returns_only_the_public_profile(self):
        response = APIClient().get(LOOKUP_URL, {'subdomain': TEST_SCHEMA})

        self.assertEqual(response.status_code, 200)
        church = response.json()['church']
        self.assertEqual(set(church), PUBLIC_FIELDS)
        self.assertEqual(church['name'], 'Lookup Parish')
        self.assertNotIn('should-never-leak', response.content.decode())
        self.assertNotIn('sk_test_should_never_leak', response.content.decode())

    def test_lookup_of_inactive_church_returns_404(self):
        self.church.is_active = False
        self.church.save(update_fields=['is_active'])

        response = APIClient().get(LOOKUP_URL, {'subdomain': TEST_SCHEMA})

        self.assertEqual(response.status_code, 404)

    def test_lookup_without_subdomain_returns_400(self):
        response = APIClient().get(LOOKUP_URL)

        self.assertEqual(response.status_code, 400)
