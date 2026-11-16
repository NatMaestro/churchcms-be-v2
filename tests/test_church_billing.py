"""
Church admins can see their own billing history, nobody else's, and still
reach their billing information after their subscription has expired.
"""
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.db import connection
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.authentication.models import User
from apps.churches.models import Church
from apps.churches.models_subscription_payment import SubscriptionPayment


def make_church(subdomain, **fields):
    with mock.patch.object(Church, 'auto_create_schema', False):
        return Church.objects.create(schema_name=subdomain, subdomain=subdomain, name=subdomain.title(),
                                     email=f'office@{subdomain}.example.test', **fields)


def make_user(church, role, email):
    return User.objects.create_user(email=email, password='pass-12345', name=role.title(), church=church, role=role)


def pay(church, reference, days_ago, status='completed'):
    return SubscriptionPayment.objects.create(
        church=church, amount=Decimal('29.00'), plan='standard', duration='monthly', reference=reference,
        status=status, user_email='admin@example.test', completed_at=timezone.now() - timedelta(days=days_ago),
    )


class BillingHistoryTests(TestCase):
    def setUp(self):
        connection.set_schema_to_public()
        self.church = make_church('billingchurch', plan='standard')
        self.admin = make_user(self.church, 'admin', 'admin@billing.example.test')

    def tearDown(self):
        connection.set_schema_to_public()

    def history_as(self, user, church=None, **headers):
        client = APIClient()
        client.force_authenticate(user=user)
        return client.get(f'/api/v1/churches/{(church or self.church).id}/subscription-payments/', **headers)

    def test_admin_sees_completed_payments_newest_first(self):
        pay(self.church, 'OLD', days_ago=40)
        pay(self.church, 'NEW', days_ago=5)
        pay(self.church, 'PENDING', days_ago=1, status='pending')

        response = self.history_as(self.admin)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([p['reference'] for p in response.data['payments']], ['NEW', 'OLD'])
        self.assertEqual(response.data['payments'][0]['amount'], '29.00')

    def test_members_cannot_see_billing(self):
        member = make_user(self.church, 'member', 'member@billing.example.test')

        self.assertEqual(self.history_as(member).status_code, 403)

    def test_another_churchs_admin_cannot_see_it(self):
        other = make_church('otherbilling')
        other_admin = make_user(other, 'admin', 'admin@otherbilling.example.test')
        pay(self.church, 'PRIVATE', days_ago=2)

        response = self.history_as(other_admin)

        self.assertEqual(response.status_code, 404)

    def test_an_expired_church_can_still_read_its_billing_info(self):
        Church.objects.filter(pk=self.church.pk).update(
            plan='trial', trial_end_date=timezone.now() - timedelta(days=60))
        client = APIClient()
        client.force_authenticate(user=self.admin)
        header = {'HTTP_X_TENANT_SUBDOMAIN': self.church.subdomain}

        history = client.get(f'/api/v1/churches/{self.church.id}/subscription-payments/', **header)
        status_ = client.get(f'/api/v1/churches/{self.church.id}/subscription_status/', **header)
        elsewhere = client.get('/api/v1/churches/', **header)

        self.assertEqual(history.status_code, 200)
        self.assertEqual(status_.status_code, 200)
        self.assertEqual(status_.data['status'], 'trial_expired')
        self.assertEqual(elsewhere.status_code, 403)
