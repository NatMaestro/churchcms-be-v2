"""
The tenant is chosen by the client-supplied X-Tenant-Subdomain header, so a user
of church A used to be able to read church B's data just by sending B's
subdomain. These tests go through the real middleware stack and real JWTs.
"""
from django.conf import settings
from django.db import connection
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import User
from apps.churches.models import Church
from apps.members.models import Member

MEMBERS_URL = '/api/v1/members/'
TEST_SCHEMAS = ('bindinga', 'bindingb')


class TenantBindingTests(TransactionTestCase):
    # Setting available_apps makes Django flush with TRUNCATE ... CASCADE, so
    # tenant schemas left behind by other test modules (whose tables hold
    # foreign keys to public.churches) cannot block the flush after each test.
    available_apps = list(settings.INSTALLED_APPS)

    def setUp(self):
        connection.set_schema_to_public()
        self.church_a = self._make_church(TEST_SCHEMAS[0])
        self.church_b = self._make_church(TEST_SCHEMAS[1])

        connection.set_tenant(self.church_b)
        Member.objects.create(
            member_id='B-0001', first_name='Only', last_name='InB', email='only-in-b@example.test',
        )
        connection.set_schema_to_public()

        self.admin_a = User.objects.create_user(
            email='admin@binding-a.test', password='pass-12345', name='Admin A',
            church=self.church_a, role='admin',
        )
        self.churchless = User.objects.create_user(
            email='nochurch@binding.test', password='pass-12345', name='No Church',
        )
        self.superadmin = User.objects.create_user(
            email='super@binding.test', password='pass-12345', name='Super',
            role='superadmin',
        )

    def tearDown(self):
        # Drop the tenant schemas directly. Church.delete() cascades into
        # tenant-only tables that do not exist in the public schema, and any
        # schema left behind blocks TransactionTestCase's flush (its tables
        # hold foreign keys to public.churches). Flush then removes the rows.
        connection.set_schema_to_public()
        with connection.cursor() as cursor:
            for schema in TEST_SCHEMAS:
                cursor.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')

    @staticmethod
    def _make_church(subdomain):
        return Church.objects.create(
            schema_name=subdomain, subdomain=subdomain, name=subdomain.title(),
            email=f'office@{subdomain}.example.test', bypass_subscription_check=True,
        )

    @staticmethod
    def _client(user, subdomain):
        client = APIClient()
        token = RefreshToken.for_user(user).access_token
        client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {token}', HTTP_X_TENANT_SUBDOMAIN=subdomain,
        )
        return client

    def test_admin_of_church_a_cannot_read_church_b_members(self):
        response = self._client(self.admin_a, 'bindingb').get(MEMBERS_URL)

        self.assertEqual(response.status_code, 401)
        self.assertNotIn('only-in-b@example.test', response.content.decode())

    def test_user_without_a_church_cannot_read_any_church(self):
        response = self._client(self.churchless, 'bindingb').get(MEMBERS_URL)

        self.assertEqual(response.status_code, 401)

    def test_admin_can_still_read_their_own_church(self):
        response = self._client(self.admin_a, 'bindinga').get(MEMBERS_URL)

        self.assertEqual(response.status_code, 200)

    def test_superadmin_keeps_platform_wide_access(self):
        response = self._client(self.superadmin, 'bindingb').get(MEMBERS_URL)

        self.assertEqual(response.status_code, 200)
        self.assertIn('only-in-b@example.test', response.content.decode())
