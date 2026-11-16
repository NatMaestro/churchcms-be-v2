"""
Platform admin API: only platform superadmins can use it; mark-as-paid,
trial extension, suspension and free access follow the subscription rules;
plans are editable but never deleted or renamed.
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
from apps.churches.models_plan import Plan
from apps.churches.models_subscription_payment import SubscriptionPayment
from apps.churches.subscriptions import account_state, account_state_filter, start_trial

BASE = '/api/v1/platform'


def make_church(subdomain, **fields):
    with mock.patch.object(Church, 'auto_create_schema', False):
        return Church.objects.create(schema_name=subdomain, subdomain=subdomain, name=subdomain.title(),
                                     email=f'office@{subdomain}.example.test', **fields)


class PlatformTestCase(TestCase):
    def setUp(self):
        connection.set_schema_to_public()
        self.church = make_church('platformchurch')
        start_trial(self.church)
        self.church.save()
        self.superadmin = User.objects.create_user(email='owner@platform.example.test', password='pass-12345',
                                                   name='Platform Owner', role='superadmin')
        self.church_admin = User.objects.create_user(email='admin@platformchurch.example.test',
                                                     password='pass-12345', name='Church Admin',
                                                     church=self.church, role='admin')
        self.client = APIClient()
        self.client.force_authenticate(user=self.superadmin)

    def tearDown(self):
        connection.set_schema_to_public()

    def post(self, path, data=None):
        return self.client.post(f'{BASE}{path}', data or {}, format='json')

    def record_payment(self, **overrides):
        data = {'plan': 'standard', 'duration': 'monthly', 'method': 'mobile_money', 'reference': 'MOMO-1'}
        data.update(overrides)
        return self.post(f'/churches/{self.church.id}/record-payment/', data)


class OnlySuperadminsTests(PlatformTestCase):
    ENDPOINTS = [('get', '/overview/'), ('get', '/churches/'), ('get', '/plans/'), ('get', '/payments/'),
                 ('post', '/plans/'), ('post', '/churches/{id}/record-payment/'),
                 ('post', '/churches/{id}/extend-trial/'), ('post', '/churches/{id}/suspend/'),
                 ('post', '/churches/{id}/free-access/')]

    def call_all(self, client):
        return {path: getattr(client, method)(f'{BASE}{path.format(id=self.church.id)}', {}, format='json')
                for method, path in self.ENDPOINTS}

    def test_a_church_admin_is_refused_everywhere(self):
        client = APIClient()
        client.force_authenticate(user=self.church_admin)

        for path, response in self.call_all(client).items():
            self.assertEqual(response.status_code, 403, path)

    def test_anonymous_visitors_are_refused_everywhere(self):
        for path, response in self.call_all(APIClient()).items():
            self.assertIn(response.status_code, (401, 403), path)


class RecordPaymentTests(PlatformTestCase):
    def test_marks_the_church_paid_at_the_plan_price(self):
        response = self.record_payment()

        self.assertEqual(response.status_code, 201, response.content)
        payment = SubscriptionPayment.objects.get(reference='MOMO-1')
        self.assertEqual(payment.amount, Decimal('29.00'))
        self.assertEqual(payment.payment_method, 'mobile_money')
        self.assertEqual(payment.recorded_by, self.superadmin)
        self.assertEqual(payment.status, 'completed')
        self.church.refresh_from_db()
        self.assertEqual(self.church.plan, 'standard')
        self.assertEqual(account_state(self.church), 'paying')
        self.assertEqual(response.data['church']['account_state'], 'paying')

    def test_records_the_amount_actually_received(self):
        self.record_payment(amount='25.00', note='Discount agreed on the demo call')

        payment = SubscriptionPayment.objects.get(reference='MOMO-1')
        self.assertEqual(payment.amount, Decimal('25.00'))
        self.assertEqual(payment.note, 'Discount agreed on the demo call')

    def test_recording_the_same_reference_twice_adds_time_once(self):
        self.record_payment()
        self.church.refresh_from_db()
        first_end = self.church.subscription_end_date

        response = self.record_payment()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['already_recorded'])
        self.church.refresh_from_db()
        self.assertEqual(self.church.subscription_end_date, first_end)
        self.assertEqual(SubscriptionPayment.objects.count(), 1)

    def test_a_reference_used_by_another_church_is_a_conflict(self):
        other = make_church('otherplatformchurch')
        SubscriptionPayment.objects.create(church=other, amount=Decimal('29.00'), plan='standard',
                                           reference='MOMO-1', user_email='x@example.test')

        response = self.record_payment()

        self.assertEqual(response.status_code, 409)
        self.church.refresh_from_db()
        self.assertEqual(self.church.plan, 'trial')

    def test_unknown_plan_is_rejected(self):
        response = self.record_payment(plan='platinum')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(SubscriptionPayment.objects.exists())

    def test_yearly_needs_an_amount_when_the_plan_has_no_yearly_price(self):
        Plan.objects.filter(code='standard').update(price_yearly=None)

        response = self.record_payment(duration='yearly')

        self.assertEqual(response.status_code, 400)

    def test_a_blank_reference_is_rejected(self):
        response = self.record_payment(reference='   ')

        self.assertEqual(response.status_code, 400)


class TrialAndAccessTests(PlatformTestCase):
    def test_extending_a_trial_adds_days_to_its_end(self):
        original_end = self.church.trial_end_date

        response = self.post(f'/churches/{self.church.id}/extend-trial/', {'days': 14})

        self.assertEqual(response.status_code, 200)
        self.church.refresh_from_db()
        self.assertEqual(self.church.trial_end_date, original_end + timedelta(days=14))

    def test_extending_an_ended_trial_counts_from_today(self):
        Church.objects.filter(pk=self.church.pk).update(trial_end_date=timezone.now() - timedelta(days=20))

        self.post(f'/churches/{self.church.id}/extend-trial/', {'days': 7})

        self.church.refresh_from_db()
        self.assertAlmostEqual(self.church.trial_end_date, timezone.now() + timedelta(days=7),
                               delta=timedelta(minutes=1))

    def test_a_paying_church_cannot_get_trial_days(self):
        self.record_payment()

        response = self.post(f'/churches/{self.church.id}/extend-trial/', {'days': 7})

        self.assertEqual(response.status_code, 400)

    def test_trial_extensions_are_bounded(self):
        for days in (0, 91):
            response = self.post(f'/churches/{self.church.id}/extend-trial/', {'days': days})
            self.assertEqual(response.status_code, 400, days)

    def test_suspending_and_reactivating_a_church(self):
        response = self.post(f'/churches/{self.church.id}/suspend/', {'enabled': True})
        self.assertEqual(response.data['church']['account_state'], 'suspended')

        response = self.post(f'/churches/{self.church.id}/suspend/', {'enabled': False})
        self.assertEqual(response.data['church']['account_state'], 'trial')

    def test_free_access_marks_a_church_free(self):
        response = self.post(f'/churches/{self.church.id}/free-access/', {'enabled': True})

        self.assertEqual(response.data['church']['account_state'], 'free')
        self.church.refresh_from_db()
        self.assertTrue(self.church.bypass_subscription_check)


class ChurchListTests(PlatformTestCase):
    def test_state_filter_and_search(self):
        make_church('freeparish', bypass_subscription_check=True)

        free = self.client.get(f'{BASE}/churches/', {'state': 'free'}).data['results']
        found = self.client.get(f'{BASE}/churches/', {'search': 'platformch'}).data['results']

        self.assertEqual([church['subdomain'] for church in free], ['freeparish'])
        self.assertEqual([church['subdomain'] for church in found], ['platformchurch'])
        self.assertEqual(found[0]['user_count'], 1)

    def test_list_filters_agree_with_each_churchs_label(self):
        now = timezone.now()
        churches = [
            make_church('stateone', plan='trial', trial_end_date=now + timedelta(days=3)),
            make_church('statetwo', plan='trial', trial_end_date=now - timedelta(days=3)),
            make_church('statethree', plan='standard', subscription_end_date=now + timedelta(days=3)),
            make_church('statefour', plan='standard', subscription_end_date=now - timedelta(days=3)),
            make_church('statefive', bypass_subscription_check=True),
            make_church('statesix', subscription_status='suspended', bypass_subscription_check=True),
        ]
        for church in churches:
            matching = Church.objects.filter(account_state_filter(account_state(church, now), now))
            self.assertIn(church, matching, church.subdomain)

    def test_detail_includes_recent_payments(self):
        self.record_payment()

        response = self.client.get(f'{BASE}/churches/{self.church.id}/')

        self.assertEqual([p['reference'] for p in response.data['recent_payments']], ['MOMO-1'])


class PlanAdminTests(PlatformTestCase):
    def test_lists_every_plan_including_hidden_ones(self):
        Plan.objects.filter(code='enterprise').update(is_public=False)

        response = self.client.get(f'{BASE}/plans/')

        self.assertEqual(len(response.data), 4)

    def test_create_and_edit_a_plan(self):
        response = self.post('/plans/', {'code': 'parish', 'name': 'Parish', 'price_monthly': '120.00',
                                         'features': ['Up to 300 members', '  ', 'WhatsApp support']})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.data['features'], ['Up to 300 members', 'WhatsApp support'])

        response = self.client.patch(f"{BASE}/plans/{response.data['id']}/", {'price_monthly': '150.00'},
                                     format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Plan.objects.get(code='parish').price_monthly, Decimal('150.00'))

    def test_a_plan_code_cannot_be_renamed(self):
        plan = Plan.objects.get(code='basic')

        response = self.client.patch(f'{BASE}/plans/{plan.id}/', {'code': 'starter'}, format='json')

        self.assertEqual(response.status_code, 400)

    def test_trial_is_not_a_plan_code(self):
        response = self.post('/plans/', {'code': 'trial', 'name': 'Trial', 'price_monthly': '1.00'})

        self.assertEqual(response.status_code, 400)

    def test_prices_must_be_positive(self):
        response = self.post('/plans/', {'code': 'zero', 'name': 'Zero', 'price_monthly': '0.00'})

        self.assertEqual(response.status_code, 400)

    def test_plans_cannot_be_deleted(self):
        plan = Plan.objects.get(code='basic')

        response = self.client.delete(f'{BASE}/plans/{plan.id}/')

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Plan.objects.filter(code='basic').exists())


class OverviewTests(PlatformTestCase):
    def test_counts_churches_and_this_months_revenue(self):
        self.record_payment(amount='40.00')
        make_church('anotherfree', bypass_subscription_check=True)

        data = self.client.get(f'{BASE}/overview/').data

        self.assertEqual(data['churches_total'], 2)
        self.assertEqual(data['churches_by_state']['paying'], 1)
        self.assertEqual(data['churches_by_state']['free'], 1)
        self.assertEqual(Decimal(data['revenue_this_month']), Decimal('40.00'))
        self.assertEqual(data['payments_this_month'], 1)


class ChurchCannotEditItsOwnSubscriptionTests(PlatformTestCase):
    def test_a_church_admin_cannot_give_their_church_free_access_or_time(self):
        client = APIClient()
        client.force_authenticate(user=self.church_admin)
        original_end = self.church.trial_end_date

        client.patch(f'/api/v1/churches/{self.church.id}/', {
            'bypass_subscription_check': True, 'plan': 'enterprise',
            'trial_end_date': (timezone.now() + timedelta(days=3650)).isoformat(),
        }, format='json')

        self.church.refresh_from_db()
        self.assertFalse(self.church.bypass_subscription_check)
        self.assertEqual(self.church.plan, 'trial')
        self.assertEqual(self.church.trial_end_date, original_end)
