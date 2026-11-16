"""
The Paystack webhook is unauthenticated. It used to accept any POST, so a forged
`charge.success` could activate a paid subscription for free.
"""
import hashlib
import hmac
import json
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from apps.churches import views_payment
from apps.churches.models import Church
from apps.churches.models_subscription_payment import SubscriptionPayment

WEBHOOK_URL = '/api/v1/churches/subscription-payment/webhook/'
TEST_SECRET = 'sk_test_unit_test_only'


def sign(body: bytes, secret: str = TEST_SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha512).hexdigest()


@mock.patch.object(views_payment, 'PAYSTACK_SECRET_KEY', TEST_SECRET)
class PaystackWebhookTests(TestCase):
    def setUp(self):
        with mock.patch.object(Church, 'auto_create_schema', False):
            self.church = Church.objects.create(
                schema_name='webhookchurch', subdomain='webhookchurch', name='Webhook Church',
                email='office@webhook.example.test',
            )
        self.payment = SubscriptionPayment.objects.create(
            church=self.church, amount=Decimal('100.00'), plan='basic', duration='monthly',
            reference='FF-REF-1', paystack_reference='FF-REF-1', user_email='admin@webhook.example.test',
        )
        self.client = APIClient()
        self.body = json.dumps({
            'event': 'charge.success',
            'data': {'reference': 'FF-REF-1', 'amount': 10000, 'currency': 'GHS'},
        }).encode()

    def post(self, body, signature=None):
        extra = {} if signature is None else {'HTTP_X_PAYSTACK_SIGNATURE': signature}
        return self.client.post(WEBHOOK_URL, data=body, content_type='application/json', **extra)

    def assertNotActivated(self):
        self.payment.refresh_from_db()
        self.assertNotEqual(self.payment.status, 'completed')
        self.assertFalse(self.payment.subscription_activated)

    def test_unsigned_webhook_is_rejected_and_does_not_activate(self):
        response = self.post(self.body)

        self.assertEqual(response.status_code, 401)
        self.assertNotActivated()

    def test_webhook_signed_with_wrong_secret_is_rejected(self):
        response = self.post(self.body, sign(self.body, 'sk_test_attacker_guess'))

        self.assertEqual(response.status_code, 401)
        self.assertNotActivated()

    def test_signature_for_a_different_body_is_rejected(self):
        response = self.post(self.body, sign(b'{"event":"charge.failed"}'))

        self.assertEqual(response.status_code, 401)
        self.assertNotActivated()

    def test_correctly_signed_webhook_activates_subscription(self):
        response = self.post(self.body, sign(self.body))

        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'completed')
        self.assertTrue(self.payment.subscription_activated)

    def test_replayed_webhook_is_harmless(self):
        self.post(self.body, sign(self.body))
        self.payment.refresh_from_db()
        first_end = self.payment.subscription_end_date

        response = self.post(self.body, sign(self.body))

        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.subscription_end_date, first_end)

    def test_webhook_fails_closed_when_secret_is_not_configured(self):
        with mock.patch.object(views_payment, 'PAYSTACK_SECRET_KEY', ''):
            response = self.post(self.body, sign(self.body, ''))

        self.assertEqual(response.status_code, 503)
        self.assertNotActivated()
