"""
Subscription rules: plans from the database, trials that start once on the
server, paid periods that extend instead of resetting, Paystack charges that
must match the price, and expired churches that can still reach payment.
"""
import hashlib
import hmac
import json
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.db import connection
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.authentication.models import User
from apps.churches import views_payment
from apps.churches.models import Church
from apps.churches.models_plan import Plan
from apps.churches.models_subscription_payment import SubscriptionPayment
from apps.churches.subscriptions import (TRIAL_DAYS, activate_paid_period, start_trial,
                                         to_minor_units)

TEST_SECRET = 'sk_test_unit_test_only'
PLANS_URL = '/api/v1/plans/'
INITIALIZE_URL = '/api/v1/churches/subscription-payment/initialize/'
VERIFY_URL = '/api/v1/churches/subscription-payment/verify/'
WEBHOOK_URL = '/api/v1/churches/subscription-payment/webhook/'
ONE_SECOND = timedelta(seconds=1)


class PublicSchemaTestCase(TestCase):
    """Requests sent with a church header switch the connection to that church; switch back."""

    def setUp(self):
        connection.set_schema_to_public()
        super().setUp()

    def tearDown(self):
        connection.set_schema_to_public()
        super().tearDown()


def make_church(subdomain, **fields):
    with mock.patch.object(Church, 'auto_create_schema', False):
        return Church.objects.create(schema_name=subdomain, subdomain=subdomain, name=subdomain.title(),
                                     email=f'office@{subdomain}.example.test', **fields)


def make_payment(church, amount='29.00', duration='monthly', reference='SUB-TEST-1', plan='standard'):
    return SubscriptionPayment.objects.create(
        church=church, amount=Decimal(amount), plan=plan, duration=duration, reference=reference,
        paystack_reference=reference, status='processing', user_email='admin@example.test',
    )


def paystack_verify_response(amount, currency='GHS'):
    response = mock.Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {'status': True, 'data': {'status': 'success', 'amount': amount,
                                                           'currency': currency}}
    return response


class MinorUnitTests(PublicSchemaTestCase):
    def test_cedis_convert_to_pesewas_rounding_half_up(self):
        self.assertEqual(to_minor_units(Decimal('19.00')), 1900)
        self.assertEqual(to_minor_units(Decimal('10.125')), 1013)
        self.assertEqual(to_minor_units(Decimal('0.004')), 0)
        self.assertEqual(to_minor_units(Decimal('0.005')), 1)


class PublicPlansTests(PublicSchemaTestCase):
    def test_lists_only_active_public_plans_in_order_with_ghs_prices(self):
        Plan.objects.create(code='hidden', name='Hidden', price_monthly=Decimal('5.00'), is_public=False)
        Plan.objects.create(code='retired', name='Retired', price_monthly=Decimal('5.00'), is_active=False)

        response = APIClient().get(PLANS_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['version'], 1)
        self.assertEqual(response.data['currency'], 'GHS')
        codes = [plan['code'] for plan in response.data['plans']]
        self.assertEqual(codes, ['basic', 'standard', 'premium', 'enterprise'])
        standard = response.data['plans'][1]
        self.assertEqual(standard['price_monthly'], '29.00')
        self.assertTrue(standard['is_featured'])

    def test_a_stale_login_cookie_does_not_block_the_public_list(self):
        client = APIClient()
        client.cookies['ff_access'] = 'not-a-valid-token'

        response = client.get(PLANS_URL)

        self.assertEqual(response.status_code, 200)


class PaidPeriodTests(PublicSchemaTestCase):
    def setUp(self):
        super().setUp()
        self.church = make_church('periodchurch')

    def test_first_payment_starts_now_and_lasts_a_month(self):
        before = timezone.now()
        payment = activate_paid_period(make_payment(self.church).pk)

        self.church.refresh_from_db()
        self.assertEqual(self.church.plan, 'standard')
        self.assertIsNone(self.church.trial_end_date)
        self.assertGreaterEqual(payment.subscription_start_date, before)
        self.assertEqual(payment.subscription_end_date - payment.subscription_start_date, timedelta(days=30))
        self.assertEqual(self.church.subscription_end_date, payment.subscription_end_date)
        self.assertEqual(payment.status, 'completed')

    def test_paying_early_adds_the_month_after_the_current_end(self):
        current_end = timezone.now() + timedelta(days=10)
        Church.objects.filter(pk=self.church.pk).update(subscription_end_date=current_end, plan='standard')

        payment = activate_paid_period(make_payment(self.church).pk)

        self.assertEqual(payment.subscription_start_date, current_end)
        self.church.refresh_from_db()
        self.assertEqual(self.church.subscription_end_date, current_end + timedelta(days=30))

    def test_paying_after_expiry_starts_from_now(self):
        Church.objects.filter(pk=self.church.pk).update(subscription_end_date=timezone.now() - timedelta(days=3))
        before = timezone.now()

        payment = activate_paid_period(make_payment(self.church).pk)

        self.assertGreaterEqual(payment.subscription_start_date, before)

    def test_yearly_payment_lasts_365_days(self):
        payment = activate_paid_period(make_payment(self.church, '313.00', 'yearly').pk)

        self.assertEqual(payment.subscription_end_date - payment.subscription_start_date, timedelta(days=365))

    def test_activating_the_same_payment_twice_adds_time_only_once(self):
        payment = make_payment(self.church)
        activate_paid_period(payment.pk)
        self.church.refresh_from_db()
        first_end = self.church.subscription_end_date

        activate_paid_period(payment.pk)

        self.church.refresh_from_db()
        self.assertEqual(self.church.subscription_end_date, first_end)


@mock.patch.object(views_payment, 'PAYSTACK_SECRET_KEY', TEST_SECRET)
class PaystackChargeMustMatchPriceTests(PublicSchemaTestCase):
    def setUp(self):
        super().setUp()
        self.church = make_church('chargechurch')
        self.payment = make_payment(self.church, amount='29.00')

    def verify(self, paystack_response):
        with mock.patch.object(views_payment.requests, 'get', return_value=paystack_response):
            return APIClient().get(VERIFY_URL, {'reference': self.payment.reference})

    def assertNotActivated(self):
        self.payment.refresh_from_db()
        self.assertFalse(self.payment.subscription_activated)
        self.church.refresh_from_db()
        self.assertEqual(self.church.plan, 'trial')

    def test_verify_activates_when_the_full_price_was_paid(self):
        response = self.verify(paystack_verify_response(2900))

        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertTrue(self.payment.subscription_activated)

    def test_verify_does_not_activate_a_short_payment(self):
        response = self.verify(paystack_verify_response(100))

        self.assertEqual(response.status_code, 400)
        self.assertNotActivated()

    def test_verify_does_not_activate_a_payment_in_another_currency(self):
        response = self.verify(paystack_verify_response(2900, currency='NGN'))

        self.assertEqual(response.status_code, 400)
        self.assertNotActivated()

    def test_webhook_acknowledges_but_does_not_activate_a_short_payment(self):
        body = json.dumps({'event': 'charge.success',
                           'data': {'reference': self.payment.reference, 'amount': 100, 'currency': 'GHS'}}).encode()
        signature = hmac.new(TEST_SECRET.encode(), body, hashlib.sha512).hexdigest()

        response = APIClient().post(WEBHOOK_URL, data=body, content_type='application/json',
                                    HTTP_X_PAYSTACK_SIGNATURE=signature)

        self.assertEqual(response.status_code, 200)
        self.assertNotActivated()


@mock.patch.object(views_payment, 'PAYSTACK_SECRET_KEY', TEST_SECRET)
class InitializeUsesPlanPricesTests(PublicSchemaTestCase):
    def setUp(self):
        super().setUp()
        self.church = make_church('initchurch')
        self.admin = User.objects.create_user(email='admin@init.example.test', password='pass-12345',
                                              name='Admin', church=self.church, role='admin')
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
        gateway = mock.Mock()
        gateway.raise_for_status.return_value = None
        gateway.json.return_value = {'status': True, 'data': {
            'reference': 'REF', 'authorization_url': 'https://checkout.paystack.example.test/x'}}
        self.gateway = gateway

    def initialize(self, plan='standard', duration='monthly', **headers):
        with mock.patch.object(views_payment.requests, 'post', return_value=self.gateway) as post:
            response = self.client.post(INITIALIZE_URL, {
                'church_id': self.church.id, 'plan': plan, 'duration': duration,
                'email': 'admin@init.example.test'}, format='json', **headers)
        return response, post

    def test_charges_the_price_a_platform_admin_set(self):
        Plan.objects.filter(code='standard').update(price_monthly=Decimal('150.50'))

        response, post = self.initialize()

        self.assertEqual(response.status_code, 200)
        sent = post.call_args.kwargs['json']
        self.assertEqual(sent['amount'], 15050)
        self.assertEqual(sent['currency'], 'GHS')
        self.assertEqual(SubscriptionPayment.objects.get().amount, Decimal('150.50'))

    def test_a_retired_plan_cannot_be_bought(self):
        Plan.objects.filter(code='standard').update(is_active=False)

        response, post = self.initialize()

        self.assertEqual(response.status_code, 400)
        post.assert_not_called()

    def test_a_plan_without_a_yearly_price_cannot_be_bought_yearly(self):
        Plan.objects.filter(code='standard').update(price_yearly=None)

        response, post = self.initialize(duration='yearly')

        self.assertEqual(response.status_code, 400)
        post.assert_not_called()

    def test_an_expired_church_can_still_start_a_renewal_payment(self):
        Church.objects.filter(pk=self.church.pk).update(
            trial_end_date=timezone.now() - timedelta(days=60))

        response, _ = self.initialize(HTTP_X_TENANT_SUBDOMAIN=self.church.subdomain)

        self.assertEqual(response.status_code, 200)


class ExpiredChurchAccessTests(PublicSchemaTestCase):
    def get_as_tenant(self, church):
        user = User.objects.create_user(email=f'admin@{church.subdomain}.example.test', password='pass-12345',
                                        name='Admin', church=church, role='admin')
        client = APIClient()
        client.force_authenticate(user=user)
        return client.get('/api/v1/churches/', HTTP_X_TENANT_SUBDOMAIN=church.subdomain)

    def expired(self, subdomain, **fields):
        return make_church(subdomain, trial_end_date=timezone.now() - timedelta(days=60), **fields)

    def test_an_expired_church_is_blocked(self):
        response = self.get_as_tenant(self.expired('expiredchurch'))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.json()['upgrade_required'])

    def test_no_subdomain_is_exempt_by_name_any_more(self):
        response = self.get_as_tenant(self.expired('apostolic'))

        self.assertEqual(response.status_code, 403)

    def test_the_bypass_flag_still_exempts_a_church(self):
        response = self.get_as_tenant(self.expired('freechurch', bypass_subscription_check=True))

        self.assertEqual(response.status_code, 200)


class TrialTests(PublicSchemaTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def start_trial_as(self, user, church):
        self.client.force_authenticate(user=user)
        return self.client.post(f'/api/v1/churches/{church.id}/start-trial/')

    def test_a_church_admin_cannot_restart_their_trial(self):
        church = make_church('trialchurch')
        start_trial(church, now=timezone.now() - timedelta(days=40))
        church.save()
        original_end = church.trial_end_date
        admin = User.objects.create_user(email='admin@trial.example.test', password='pass-12345',
                                         name='Admin', church=church, role='admin')

        response = self.start_trial_as(admin, church)

        self.assertEqual(response.status_code, 200)
        church.refresh_from_db()
        self.assertEqual(church.trial_end_date, original_end)

    def test_a_church_without_a_trial_gets_one_once(self):
        church = make_church('notrialchurch')
        admin = User.objects.create_user(email='admin@notrial.example.test', password='pass-12345',
                                         name='Admin', church=church, role='admin')

        response = self.start_trial_as(admin, church)

        self.assertEqual(response.status_code, 200)
        church.refresh_from_db()
        self.assertAlmostEqual(church.trial_end_date, timezone.now() + timedelta(days=TRIAL_DAYS),
                               delta=timedelta(minutes=1))

    def test_a_superadmin_can_give_a_fresh_trial(self):
        church = make_church('freshtrialchurch')
        start_trial(church, now=timezone.now() - timedelta(days=40))
        church.save()
        superadmin = User.objects.create_user(email='super@trial.example.test', password='pass-12345',
                                              name='Super', role='superadmin')

        self.start_trial_as(superadmin, church)

        church.refresh_from_db()
        self.assertGreater(church.trial_end_date, timezone.now())

    def test_registering_a_church_starts_its_trial_on_the_server(self):
        response = APIClient().post('/api/v1/auth/register/', {
            'church_name': 'Grace Chapel', 'subdomain': 'gracechapeltrial', 'name': 'Pastor Ama',
            'email': 'ama@gracechapel.example.test', 'password': 'StrongPass-2026',
            'password_confirm': 'StrongPass-2026',
        }, format='json')

        self.assertEqual(response.status_code, 201, response.content)
        church = Church.objects.get(subdomain='gracechapeltrial')
        self.assertEqual(church.plan, 'trial')
        self.assertIsNotNone(church.trial_started_at)
        self.assertAlmostEqual(church.trial_end_date, church.trial_started_at + timedelta(days=TRIAL_DAYS),
                               delta=ONE_SECOND)
