"""
Giving: church staff record gifts (members give directly to the church), a
recorded gift is never edited or deleted, only reversed with a reason, and
the year summary adds up only completed gifts. The church's Mobile Money and
bank details are set by its admin and read by its members; members cannot
change the church.
"""
from datetime import datetime, timezone as dt_tz
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
from apps.payments.models import Payment

SCHEMA = 'givingchurch'
PAYMENTS = '/api/v1/payments/'


class GivingTests(TransactionTestCase):
    # See tests/test_tenant_binding.py: makes the flush use TRUNCATE ... CASCADE.
    available_apps = list(settings.INSTALLED_APPS)

    def setUp(self):
        cache.clear()
        connection.set_schema_to_public()
        self.church = Church.objects.create(schema_name=SCHEMA, subdomain=SCHEMA, name='Giving Church',
                                            email='office@giving.example.test', bypass_subscription_check=True,
                                            integration_settings={'service_key': 'not-for-members'})
        self.admin = User.objects.create_user(email='admin@giving.example.test', password='pass-12345',
                                              name='Treasurer', church=self.church, role='admin')
        self.member_user = User.objects.create_user(email='kofi@giving.example.test', password='pass-12345',
                                                    name='Kofi', church=self.church, role='member')
        with tenant_context(self.church):
            self.kofi = Member.objects.create(user=self.member_user, member_id='G-1', first_name='Kofi',
                                              last_name='Mensah')

    def tearDown(self):
        cache.clear()
        connection.set_schema_to_public()
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE')

    @staticmethod
    def _client(user):
        client = APIClient()
        token = RefreshToken.for_user(user).access_token
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}', HTTP_X_TENANT_SUBDOMAIN=SCHEMA)
        return client

    def _record(self, user=None, **fields):
        data = {'member': self.kofi.pk, 'amount': '50.00', 'type': 'tithe', 'method': 'mobile_money',
                'date': '2026-03-08T10:00:00Z', **fields}
        return self._client(user or self.admin).post(PAYMENTS, data, format='json')

    # --- recording gifts ---

    def test_staff_record_a_gift_with_a_generated_reference(self):
        response = self._record()

        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(response.data['reference'].startswith('GIFT-'))
        self.assertEqual((response.data['status'], response.data['currency'], response.data['fiscal_year']),
                         ('completed', 'GHS', 2026))

    def test_the_offices_own_receipt_number_is_kept(self):
        self.assertEqual(self._record(reference='RCPT-0042').data['reference'], 'RCPT-0042')

    def test_a_gift_needs_a_positive_amount_and_a_member(self):
        self.assertEqual(self._record(amount='0.00').status_code, 400)
        self.assertEqual(self._record(amount='-5.00').status_code, 400)
        self.assertEqual(self._record(member=None).status_code, 400)

    def test_members_cannot_record_gifts(self):
        self.assertEqual(self._record(user=self.member_user).status_code, 403)

    # --- never edited, only reversed ---

    def test_a_recorded_gift_cannot_be_changed_or_deleted(self):
        gift_id = self._record().data['id']
        client = self._client(self.admin)

        client.patch(f'{PAYMENTS}{gift_id}/', {'amount': '5000.00', 'notes': 'Envelope 12'}, format='json')

        with tenant_context(self.church):
            gift = Payment.objects.get(pk=gift_id)
        self.assertEqual((gift.amount, gift.notes), (Decimal('50.00'), 'Envelope 12'))  # only notes change
        self.assertEqual(client.delete(f'{PAYMENTS}{gift_id}/').status_code, 405)
        self.assertEqual(client.put(f'{PAYMENTS}{gift_id}/', {}, format='json').status_code, 405)

    def test_reversing_a_gift_keeps_it_with_the_reason(self):
        gift_id = self._record(notes='Envelope 12').data['id']

        response = self._client(self.admin).post(f'{PAYMENTS}{gift_id}/reverse/', {'reason': 'Wrong member'},
                                                 format='json')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data['status'], 'refunded')
        self.assertIn('Envelope 12', response.data['notes'])
        self.assertIn('by Treasurer: Wrong member', response.data['notes'])

    def test_a_reversal_needs_a_reason_and_happens_once(self):
        gift_id = self._record().data['id']
        client = self._client(self.admin)

        self.assertEqual(client.post(f'{PAYMENTS}{gift_id}/reverse/', {}, format='json').status_code, 400)
        self.assertEqual(client.post(f'{PAYMENTS}{gift_id}/reverse/', {'reason': 'x'}, format='json').status_code, 200)
        self.assertEqual(client.post(f'{PAYMENTS}{gift_id}/reverse/', {'reason': 'x'}, format='json').status_code, 400)

    def test_members_cannot_reverse_gifts(self):
        gift_id = self._record().data['id']

        response = self._client(self.member_user).post(f'{PAYMENTS}{gift_id}/reverse/', {'reason': 'x'},
                                                       format='json')

        self.assertEqual(response.status_code, 403)

    # --- summary ---

    def test_the_year_summary_adds_up_completed_gifts_only(self):
        self._record(amount='50.00', type='tithe', date='2026-03-08T10:00:00Z')
        self._record(amount='20.50', type='offering', date='2026-03-15T10:00:00Z')
        self._record(amount='10.00', type='offering', date='2026-11-01T10:00:00Z')
        reversed_id = self._record(amount='999.00', type='tithe', date='2026-03-22T10:00:00Z').data['id']
        self._client(self.admin).post(f'{PAYMENTS}{reversed_id}/reverse/', {'reason': 'Typo'}, format='json')
        self._record(amount='77.00', date='2025-12-31T10:00:00Z')  # another year

        summary = self._client(self.admin).get(f'{PAYMENTS}summary/', {'year': 2026}).data

        self.assertEqual((Decimal(summary['total']), summary['count']), (Decimal('80.50'), 3))
        months = {row['month']: Decimal(row['total']) for row in summary['by_month']}
        self.assertEqual((months[3], months[11], months[1]), (Decimal('70.50'), Decimal('10.00'), Decimal('0')))
        self.assertEqual({k: Decimal(v) for k, v in summary['by_type'].items()},
                         {'tithe': Decimal('50.00'), 'offering': Decimal('30.50')})

    # --- the church's giving details ---

    def _details_url(self):
        return f'/api/v1/churches/{self.church.pk}/giving-details/'

    def test_the_admin_sets_giving_details_and_members_see_them(self):
        details = {'momo_network': 'mtn', 'momo_number': '0241234567', 'momo_name': 'Giving Church',
                   'bank_name': 'GCB Bank', 'bank_account_name': 'Giving Church', 'bank_account_number': '1234567890',
                   'instructions': 'Use your member ID as the reference.'}

        response = self._client(self.admin).put(self._details_url(), details, format='json')

        self.assertEqual(response.status_code, 200, response.content)
        seen = self._client(self.member_user).get(self._details_url()).data
        self.assertEqual((seen['momo_number'], seen['bank_account_number'], seen['updated_by_name']),
                         ('0241234567', '1234567890', 'Treasurer'))

    def test_bad_giving_details_are_refused(self):
        client = self._client(self.admin)
        for details in ({'momo_number': '12345'}, {'momo_number': '0241234567'},  # no network
                        {'bank_account_number': '12-34'}, {'momo_network': 'paypal'}):
            self.assertEqual(client.put(self._details_url(), details, format='json').status_code, 400, details)

    def test_members_cannot_change_giving_details(self):
        response = self._client(self.member_user).put(self._details_url(),
                                                      {'momo_network': 'mtn', 'momo_number': '0249999999'},
                                                      format='json')

        self.assertEqual(response.status_code, 403)

    # --- members cannot change the church ---

    def test_members_cannot_change_the_church_or_its_settings(self):
        client = self._client(self.member_user)
        url = f'/api/v1/churches/{self.church.pk}/'

        self.assertEqual(client.patch(url, {'name': 'Hijacked'}, format='json').status_code, 403)
        self.assertEqual(client.put(f'{url}church_settings/', {'type': 'payment', 'data': {'x': 1}},
                                    format='json').status_code, 403)
        self.assertEqual(client.post('/api/v1/churches/', {'name': 'New', 'subdomain': 'newone'},
                                     format='json').status_code, 403)
        self.church.refresh_from_db()
        self.assertEqual(self.church.name, 'Giving Church')

    def test_the_church_admin_can_still_update_the_church(self):
        response = self._client(self.admin).patch(f'/api/v1/churches/{self.church.pk}/', {'phone': '0302123456'},
                                                  format='json')

        self.assertEqual(response.status_code, 200, response.content)

    def test_members_never_see_integration_settings(self):
        member_view = self._client(self.member_user).get(f'/api/v1/churches/{self.church.pk}/').data
        admin_view = self._client(self.admin).get(f'/api/v1/churches/{self.church.pk}/').data

        self.assertNotIn('integration_settings', member_view)
        self.assertEqual(admin_view['integration_settings'], {'service_key': 'not-for-members'})
