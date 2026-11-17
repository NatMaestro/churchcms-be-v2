"""
Dues (the digital dues card): plans paid monthly or yearly, categories with
their own amounts and age ranges, staff assignments and exemptions, payments
checked against the card, reversal instead of editing, the arrears list, and
members seeing only their own card.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.test import TransactionTestCase
from django_tenants.utils import tenant_context
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import User
from apps.churches.models import Church
from apps.dues.models import DuesCategory, DuesPayment, DuesPlan
from apps.members.models import Member

SCHEMA = 'dueschurch'
DUES = '/api/v1/dues/'
# Freeze "today" at 15 May 2027: January-May of a 2027 monthly plan are due.
TODAY = date(2027, 5, 15)


def frozen_today():
    return TODAY


class DuesTests(TransactionTestCase):
    # See tests/test_tenant_binding.py: makes the flush use TRUNCATE ... CASCADE.
    available_apps = list(settings.INSTALLED_APPS)

    def setUp(self):
        cache.clear()
        connection.set_schema_to_public()
        self.church = Church.objects.create(schema_name=SCHEMA, subdomain=SCHEMA, name='St Dues',
                                            email='office@dues.example.test', bypass_subscription_check=True)
        self.admin = User.objects.create_user(email='admin@dues.example.test', password='pass-12345',
                                              name='Secretary', church=self.church, role='admin')
        self.kofi_user = User.objects.create_user(email='kofi@dues.example.test', password='pass-12345',
                                                  name='Kofi', church=self.church, role='member')
        with tenant_context(self.church):
            # Ages on 1 Jan 2027: Kofi 40 (worker), Ama 21 (student), Yaw 10 (too young), Esi no birth date.
            self.kofi = Member.objects.create(user=self.kofi_user, member_id='D-1', first_name='Kofi',
                                              last_name='Mensah', date_of_birth=date(1986, 6, 1))
            self.ama = Member.objects.create(member_id='D-2', first_name='Ama', last_name='Owusu',
                                             date_of_birth=date(2005, 3, 1))
            self.yaw = Member.objects.create(member_id='D-3', first_name='Yaw', last_name='Boateng',
                                             date_of_birth=date(2016, 2, 1))
            self.esi = Member.objects.create(member_id='D-4', first_name='Esi', last_name='Asante')
            self.plan = DuesPlan.objects.create(name='Parish dues', year=2027, frequency='monthly')
            self.workers = DuesCategory.objects.create(plan=self.plan, name='Workers', amount=Decimal('20.00'),
                                                       min_age=26)
            self.students = DuesCategory.objects.create(plan=self.plan, name='Students', amount=Decimal('5.00'),
                                                        min_age=18, max_age=25)
        patcher = mock.patch('apps.dues.services.timezone.localdate', frozen_today)
        patcher.start()
        self.addCleanup(patcher.stop)

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

    def _pay(self, member, amount, months=(), plan=None, **extra):
        return self._client(self.admin).post(f'{DUES}payments/', {
            'plan': (plan or self.plan).pk, 'member': member.pk, 'amount': amount, 'months': list(months),
            'date': '2027-05-10', 'method': 'cash', **extra,
        }, format='json')

    def _card(self, member, plan=None):
        return self._client(self.admin).get(f'{DUES}member-card/',
                                            {'plan': (plan or self.plan).pk, 'member': member.pk}).data

    # --- categories by age, assignments, exemptions ---

    def test_members_are_placed_by_age_on_1_january(self):
        self.assertEqual(self._card(self.kofi)['category']['name'], 'Workers')
        self.assertEqual(self._card(self.ama)['category']['name'], 'Students')
        yaw = self._card(self.yaw)
        self.assertEqual((yaw['category'], yaw['category_source'], yaw['owes']), (None, 'unassigned', False))

    def test_a_member_without_a_birth_date_needs_a_category_from_staff(self):
        self.assertEqual(self._card(self.esi)['category_source'], 'unassigned')

        self._client(self.admin).post(f'{DUES}assignments/', {'plan': self.plan.pk, 'member': self.esi.pk,
                                                              'category': self.students.pk}, format='json')

        card = self._card(self.esi)
        self.assertEqual((card['category']['name'], card['category_source']), ('Students', 'assigned'))

    def test_an_exempt_member_owes_nothing_and_cannot_be_charged(self):
        self._client(self.admin).post(f'{DUES}assignments/', {'plan': self.plan.pk, 'member': self.kofi.pk,
                                                              'is_exempt': True, 'note': 'Pensioner'},
                                      format='json')

        card = self._card(self.kofi)
        self.assertEqual((card['owes'], card['arrears']), (False, Decimal('0.00')))
        self.assertEqual(self._pay(self.kofi, '20.00', [1]).status_code, 400)

    # --- monthly plan: worked examples ---

    def test_paying_months_marks_them_on_the_card_with_the_receipt(self):
        response = self._pay(self.kofi, '60.00', [1, 2, 3], reference='BOOK-0042')

        self.assertEqual(response.status_code, 201, response.content)
        card = self._card(self.kofi)
        paid = {m['month']: m for m in card['months'] if m['paid']}
        self.assertEqual(sorted(paid), [1, 2, 3])
        self.assertEqual(paid[2]['reference'], 'BOOK-0042')
        # Today is 15 May 2027: April and May are due and unpaid -> 2 x GH₵20 = GH₵40.
        self.assertEqual((card['months_in_arrears'], card['arrears']), ([4, 5], Decimal('40.00')))

    def test_the_amount_must_match_the_months_at_the_members_rate(self):
        response = self._pay(self.ama, '20.00', [1, 2, 3])  # students: 3 x GH₵5 = GH₵15

        self.assertEqual(response.status_code, 400)
        self.assertIn('GH₵15.00', response.data['error'])
        self.assertEqual(self._pay(self.ama, '15.00', [1, 2, 3]).status_code, 201)

    def test_paying_in_advance_is_allowed_but_a_month_cannot_be_paid_twice(self):
        self.assertEqual(self._pay(self.kofi, '40.00', [11, 12]).status_code, 201)

        response = self._pay(self.kofi, '40.00', [12, 1])

        self.assertEqual(response.status_code, 400)
        self.assertIn('December', response.data['error'])

    def test_a_payment_needs_its_months(self):
        self.assertEqual(self._pay(self.kofi, '20.00', []).status_code, 400)

    def test_a_receipt_number_is_used_only_once(self):
        self._pay(self.kofi, '20.00', [1], reference='BOOK-1')

        self.assertEqual(self._pay(self.ama, '5.00', [1], reference='BOOK-1').status_code, 400)

    # --- yearly plan ---

    def test_a_yearly_plan_tracks_the_balance_and_refuses_overpayment(self):
        with tenant_context(self.church):
            yearly = DuesPlan.objects.create(name='Annual levy', year=2027, frequency='yearly')
            DuesCategory.objects.create(plan=yearly, name='Adults', amount=Decimal('120.00'), min_age=18)

        self.assertEqual(self._pay(self.kofi, '50.00', plan=yearly).status_code, 201)
        card = self._card(self.kofi, yearly)
        self.assertEqual((card['amount_due'], card['paid_total'], card['balance']),
                         (Decimal('120.00'), Decimal('50.00'), Decimal('70.00')))
        self.assertEqual(self._pay(self.kofi, '70.01', plan=yearly).status_code, 400)
        self.assertEqual(self._pay(self.kofi, '70.00', plan=yearly).status_code, 201)
        self.assertEqual(self._card(self.kofi, yearly)['balance'], Decimal('0.00'))

    # --- corrections ---

    def test_reversing_frees_the_months_and_keeps_the_entry(self):
        payment_id = self._pay(self.kofi, '20.00', [1]).data['id']

        response = self._client(self.admin).post(f'{DUES}payments/{payment_id}/reverse/',
                                                 {'reason': 'Wrong member'}, format='json')

        self.assertEqual((response.status_code, response.data['status']), (200, 'reversed'))
        self.assertIn('by Secretary: Wrong member', response.data['notes'])
        self.assertFalse(self._card(self.kofi)['months'][0]['paid'])
        self.assertEqual(self._pay(self.kofi, '20.00', [1]).status_code, 201)

    def test_dues_payments_cannot_be_edited_or_deleted(self):
        payment_id = self._pay(self.kofi, '20.00', [1]).data['id']
        client = self._client(self.admin)

        self.assertEqual(client.patch(f'{DUES}payments/{payment_id}/', {'amount': '1.00'},
                                      format='json').status_code, 405)
        self.assertEqual(client.delete(f'{DUES}payments/{payment_id}/').status_code, 405)

    def test_a_plan_with_payments_cannot_change_frequency(self):
        self._pay(self.kofi, '20.00', [1])

        response = self._client(self.admin).patch(f'{DUES}plans/{self.plan.pk}/', {'frequency': 'yearly'},
                                                  format='json')

        self.assertEqual(response.status_code, 400)

    # --- arrears ---

    def test_the_arrears_list_shows_who_is_behind_most_first(self):
        self._pay(self.kofi, '100.00', [1, 2, 3, 4, 5])  # up to date
        self._pay(self.ama, '5.00', [1])  # Feb-May behind: 4 x GH₵5 = GH₵20

        rows = self._client(self.admin).get(f'{DUES}plans/{self.plan.pk}/arrears/').data

        self.assertEqual([(r['member']['name'], r['arrears']) for r in rows], [('Ama Owusu', Decimal('20.00'))])

    def test_the_arrears_list_takes_a_fixed_number_of_queries(self):
        with tenant_context(self.church):
            for i in range(10):
                Member.objects.create(member_id=f'X-{i}', first_name='M', last_name=str(i),
                                      date_of_birth=date(1980, 1, 1))
        client = self._client(self.admin)
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as small:
            client.get(f'{DUES}plans/{self.plan.pk}/arrears/')
        with tenant_context(self.church):
            for i in range(10, 30):
                Member.objects.create(member_id=f'X-{i}', first_name='M', last_name=str(i),
                                      date_of_birth=date(1980, 1, 1))
        with CaptureQueriesContext(connection) as large:
            client.get(f'{DUES}plans/{self.plan.pk}/arrears/')

        self.assertEqual(len(small), len(large))

    # --- members ---

    def test_a_member_sees_only_their_own_card(self):
        self._pay(self.kofi, '20.00', [1])
        client = self._client(self.kofi_user)

        card = client.get(f'{DUES}my-card/').data
        self.assertEqual((card['member']['name'], card['category']['name']), ('Kofi Mensah', 'Workers'))
        self.assertTrue(card['months'][0]['paid'])
        self.assertEqual(client.get(f'{DUES}member-card/', {'plan': self.plan.pk, 'member': self.ama.pk}).status_code,
                         403)
        for url in ('plans/', 'payments/', 'assignments/', f'plans/{self.plan.pk}/arrears/'):
            self.assertEqual(client.get(f'{DUES}{url}').status_code, 403, url)

    def test_members_cannot_record_dues(self):
        response = self._client(self.kofi_user).post(f'{DUES}payments/', {
            'plan': self.plan.pk, 'member': self.kofi.pk, 'amount': '20.00', 'months': [1],
            'date': '2027-05-10', 'method': 'cash'}, format='json')

        self.assertEqual(response.status_code, 403)
        with tenant_context(self.church):
            self.assertFalse(DuesPayment.objects.exists())

    # --- tenants ---

    def test_another_churchs_admin_cannot_read_these_dues(self):
        other = Church.objects.create(schema_name='otherdues', subdomain='otherdues', name='Other',
                                      email='office@other.example.test', bypass_subscription_check=True)
        self.addCleanup(lambda: connection.cursor().execute('DROP SCHEMA IF EXISTS "otherdues" CASCADE'))
        outsider = User.objects.create_user(email='admin@other.example.test', password='pass-12345',
                                            name='Other admin', church=other, role='admin')
        client = self._client(outsider)  # sends this church's subdomain

        for url in ('plans/', 'payments/', f'plans/{self.plan.pk}/cards/', 'my-card/'):
            self.assertEqual(client.get(f'{DUES}{url}').status_code, 401, url)
