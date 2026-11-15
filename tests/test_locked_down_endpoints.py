"""
Endpoints that leaked internals or granted paid plans for free.
"""
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from apps.authentication.models import User
from apps.churches.models import Church


class LockedDownEndpointTests(TestCase):
    def setUp(self):
        with mock.patch.object(Church, 'auto_create_schema', False):
            self.church = Church.objects.create(
                schema_name='lockchurch', subdomain='lockchurch', name='Lock Church',
                email='office@lock.example.test', plan='trial',
            )
        self.admin = User.objects.create_user(
            email='admin@lock.test', password='pass-12345', name='Admin',
            church=self.church, role='admin',
        )
        self.superadmin = User.objects.create_user(
            email='super@lock.test', password='pass-12345', name='Super', role='superadmin',
        )

    def _upgrade_as(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client.post(
            f'/api/v1/churches/{self.church.id}/upgrade-subscription/',
            {'plan': 'enterprise', 'duration': 'yearly'}, format='json',
        )

    def test_debug_tenant_endpoint_is_gone(self):
        response = APIClient().get('/debug/tenant/')

        self.assertEqual(response.status_code, 404)

    def test_church_admin_cannot_grant_their_church_a_free_paid_plan(self):
        response = self._upgrade_as(self.admin)

        self.assertEqual(response.status_code, 403)
        self.church.refresh_from_db()
        self.assertEqual(self.church.plan, 'trial')

    def test_superadmin_can_still_set_a_plan_manually(self):
        response = self._upgrade_as(self.superadmin)

        self.assertEqual(response.status_code, 200)
        self.church.refresh_from_db()
        self.assertEqual(self.church.plan, 'enterprise')
