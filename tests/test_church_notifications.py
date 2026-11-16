"""
Automatic notifications for payments and service requests reach the right
church's admins, and recording a payment never fails because of them.
Member, payment and request rows live in the church's own schema and have no
`church` field, so the church comes from the request's tenant.
"""
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.test import TransactionTestCase
from django_tenants.utils import tenant_context
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import User
from apps.churches.models import Church
from apps.members.models import Member
from apps.notifications.models import Notification
from apps.payments.models import Payment
from apps.requests.models import ServiceRequest

TEST_SCHEMAS = ('noticea', 'noticeb')


class ChurchNotificationTests(TransactionTestCase):
    # See tests/test_tenant_binding.py: makes the flush use TRUNCATE ... CASCADE.
    available_apps = list(settings.INSTALLED_APPS)

    def setUp(self):
        cache.clear()
        connection.set_schema_to_public()
        self.church = self._make_church(TEST_SCHEMAS[0])
        self.other_church = self._make_church(TEST_SCHEMAS[1])
        self.admin = self._make_user('admin@notice-a.test', self.church, 'admin')
        self.other_admin = self._make_user('admin@notice-b.test', self.other_church, 'admin')
        self.member_user = self._make_user('kofi@notice-a.test', self.church, 'member')
        with tenant_context(self.church):
            self.member = Member.objects.create(user=self.member_user, member_id='NA-1', first_name='Kofi',
                                                last_name='Mensah', email='kofi@notice-a.test')

    def tearDown(self):
        cache.clear()
        connection.set_schema_to_public()
        with connection.cursor() as cursor:
            for schema in TEST_SCHEMAS:
                cursor.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')

    @staticmethod
    def _make_church(subdomain):
        return Church.objects.create(schema_name=subdomain, subdomain=subdomain, name=subdomain.title(),
                                     email=f'office@{subdomain}.example.test', bypass_subscription_check=True)

    @staticmethod
    def _make_user(email, church, role):
        return User.objects.create_user(email=email, password='pass-12345', name=email.split('@')[0],
                                        church=church, role=role)

    def _client(self, user):
        client = APIClient()
        token = RefreshToken.for_user(user).access_token
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}', HTTP_X_TENANT_SUBDOMAIN=user.church.subdomain)
        return client

    def _notices(self, church):
        with tenant_context(church):
            return set(Notification.objects.values_list('user_id', 'title'))

    def test_recording_a_payment_succeeds_and_notifies_the_member_and_admins(self):
        response = self._client(self.admin).post('/api/v1/payments/', {
            'member': self.member.pk, 'amount': '50.00', 'type': 'tithe', 'method': 'cash',
            'status': 'completed', 'reference': 'CASH-1', 'date': '2026-11-15',
        }, format='json')

        self.assertEqual(response.status_code, 201, response.content[:300])
        with tenant_context(self.church):
            self.assertEqual(Payment.objects.get().amount, Decimal('50.00'))
        self.assertEqual(self._notices(self.church), {
            (self.member_user.pk, 'Payment Confirmed'),
            (self.admin.pk, 'Payment Received'),
        })

    def test_another_churchs_admins_are_not_notified(self):
        self._client(self.admin).post('/api/v1/payments/', {
            'member': self.member.pk, 'amount': '20.00', 'type': 'offering', 'method': 'cash',
            'status': 'completed', 'reference': 'CASH-2', 'date': '2026-11-15',
        }, format='json')

        notified = {user_id for user_id, _ in self._notices(self.church)}
        self.assertNotIn(self.other_admin.pk, notified)

    def test_a_service_request_notifies_the_churchs_admins(self):
        connection.set_tenant(self.church)
        try:
            ServiceRequest.objects.create(member=self.member, type='counseling', title='Talk to a pastor',
                                          description='Please call me.')
        finally:
            connection.set_schema_to_public()

        self.assertEqual(self._notices(self.church), {(self.admin.pk, 'New Service Request')})
