"""
Within a church, a member sees only their own records and acts only for
themselves; church admins see and manage everyone. Covers member records,
payments, pledges, altar calls, ministry membership and event RSVPs.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone
from django_tenants.utils import tenant_context
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.altarcalls.models import AltarCall
from apps.authentication.models import User
from apps.churches.models import Church
from apps.events.models import Event, EventRegistration
from apps.members.models import Member
from apps.ministries.models import Ministry, MinistryMembership
from apps.payments.models import Payment, Pledge

SCHEMA = 'scopechurch'


def results(response):
    data = response.data
    return data['results'] if isinstance(data, dict) and 'results' in data else data


class MemberDataScopingTests(TransactionTestCase):
    # See tests/test_tenant_binding.py: makes the flush use TRUNCATE ... CASCADE.
    available_apps = list(settings.INSTALLED_APPS)

    def setUp(self):
        cache.clear()
        connection.set_schema_to_public()
        self.church = Church.objects.create(schema_name=SCHEMA, subdomain=SCHEMA, name='Scope Church',
                                            email='office@scope.example.test', bypass_subscription_check=True)
        self.admin = self._user('admin@scope.example.test', 'admin')
        self.kofi_user = self._user('kofi@scope.example.test', 'member')
        self.esi_user = self._user('esi@scope.example.test', 'member')
        self.unlinked_user = self._user('new@scope.example.test', 'member')  # login with no member record yet
        with tenant_context(self.church):
            self.kofi = Member.objects.create(user=self.kofi_user, member_id='S-1', first_name='Kofi',
                                              last_name='Mensah', email='kofi@scope.example.test')
            self.esi = Member.objects.create(user=self.esi_user, member_id='S-2', first_name='Esi',
                                             last_name='Owusu', email='esi@scope.example.test', phone='0200000002')
            for ref, member, amount in (('P-K', self.kofi, '20.00'), ('P-E', self.esi, '50.00')):
                Payment.objects.create(member=member, amount=Decimal(amount), type='tithe', method='cash',
                                       status='pending', reference=ref, date=timezone.now())
            for member in (self.kofi, self.esi):
                Pledge.objects.create(member=member, amount=Decimal('100.00'), frequency='monthly',
                                      start_date=date.today(), end_date=date.today() + timedelta(days=90))
                AltarCall.objects.create(member=member, service_date=date.today(), service_type='sunday_service',
                                         reason='salvation')
            self.choir = Ministry.objects.create(name='Choir', description='Leads worship.', category='worship')
            self.event = Event.objects.create(title='Harvest', description='Thanksgiving.', location='Hall',
                                              type='service', date=timezone.now() + timedelta(days=7))

    def tearDown(self):
        cache.clear()
        connection.set_schema_to_public()
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE')

    def _user(self, email, role):
        return User.objects.create_user(email=email, password='pass-12345', name=email.split('@')[0],
                                        church=self.church, role=role)

    @staticmethod
    def _client(user):
        client = APIClient()
        token = RefreshToken.for_user(user).access_token
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}', HTTP_X_TENANT_SUBDOMAIN=SCHEMA)
        return client

    # --- member records ---

    def test_a_member_lists_only_their_own_record(self):
        rows = results(self._client(self.kofi_user).get('/api/v1/members/'))

        self.assertEqual([row['id'] for row in rows], [self.kofi.pk])

    def test_an_admin_lists_every_member(self):
        rows = results(self._client(self.admin).get('/api/v1/members/'))

        self.assertEqual({row['id'] for row in rows}, {self.kofi.pk, self.esi.pk})

    def test_a_member_cannot_read_change_or_delete_another_member(self):
        client = self._client(self.kofi_user)
        url = f'/api/v1/members/{self.esi.pk}/'

        self.assertEqual(client.get(url).status_code, 404)
        self.assertEqual(client.patch(url, {'phone': '0209999999'}, format='json').status_code, 403)
        self.assertEqual(client.delete(url).status_code, 403)
        with tenant_context(self.church):
            self.assertEqual(Member.objects.get(pk=self.esi.pk).phone, '0200000002')

    def test_a_member_cannot_change_their_own_record_either(self):
        response = self._client(self.kofi_user).patch(f'/api/v1/members/{self.kofi.pk}/',
                                                      {'first_name': 'Changed'}, format='json')

        self.assertEqual(response.status_code, 403)

    def test_me_returns_the_signed_in_members_own_record(self):
        response = self._client(self.esi_user).get('/api/v1/members/me/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.data['id'], response.data['first_name']), (self.esi.pk, 'Esi'))

    def test_me_is_404_for_a_login_without_a_member_record(self):
        self.assertEqual(self._client(self.unlinked_user).get('/api/v1/members/me/').status_code, 404)

    # --- payments, pledges, altar calls ---

    def test_a_member_sees_only_their_own_payments(self):
        rows = results(self._client(self.kofi_user).get('/api/v1/payments/'))

        self.assertEqual([row['reference'] for row in rows], ['P-K'])

    def test_payment_statistics_for_a_member_cover_only_their_payments(self):
        response = self._client(self.kofi_user).get('/api/v1/payments/statistics/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['statistics']['total_count'], 1)

    def test_an_admin_sees_every_payment(self):
        rows = results(self._client(self.admin).get('/api/v1/payments/'))

        self.assertEqual({row['reference'] for row in rows}, {'P-K', 'P-E'})

    def test_a_member_sees_only_their_own_pledges(self):
        rows = results(self._client(self.kofi_user).get('/api/v1/payments/pledges/'))

        self.assertEqual({row['member'] for row in rows}, {self.kofi.pk})

    def test_a_member_sees_only_their_own_altar_calls(self):
        rows = results(self._client(self.kofi_user).get('/api/v1/altar-calls/'))

        self.assertEqual(len(rows), 1)
        self.assertEqual(self._client(self.admin).get('/api/v1/altar-calls/').data['count'], 2)

    # --- ministries ---

    def _ministry_row(self, user):
        rows = results(self._client(user).get('/api/v1/ministries/'))
        return next(row for row in rows if row['id'] == self.choir.pk)

    def test_a_member_joins_and_leaves_a_ministry_as_themselves(self):
        client = self._client(self.kofi_user)
        url = f'/api/v1/ministries/{self.choir.pk}/'

        self.assertEqual(client.post(url + 'join/', {}, format='json').status_code, 200)
        self.assertTrue(self._ministry_row(self.kofi_user)['is_member'])
        self.assertFalse(self._ministry_row(self.esi_user)['is_member'])
        self.assertEqual(self._ministry_row(self.kofi_user)['member_count'], 1)

        self.assertEqual(client.post(url + 'leave/', {}, format='json').status_code, 200)
        self.assertFalse(self._ministry_row(self.kofi_user)['is_member'])

    def test_a_member_can_rejoin_after_leaving(self):
        client = self._client(self.kofi_user)
        url = f'/api/v1/ministries/{self.choir.pk}/'
        client.post(url + 'join/', {}, format='json')
        client.post(url + 'leave/', {}, format='json')

        self.assertEqual(client.post(url + 'join/', {}, format='json').status_code, 200)
        self.assertTrue(self._ministry_row(self.kofi_user)['is_member'])

    def test_a_member_cannot_join_someone_else_into_a_ministry(self):
        self._client(self.kofi_user).post(f'/api/v1/ministries/{self.choir.pk}/join/',
                                          {'member_id': self.esi.pk}, format='json')

        with tenant_context(self.church):
            joined = set(MinistryMembership.objects.values_list('member_id', flat=True))
        self.assertEqual(joined, {self.kofi.pk})

    def test_an_admin_can_add_a_named_member_to_a_ministry(self):
        response = self._client(self.admin).post(f'/api/v1/ministries/{self.choir.pk}/join/',
                                                 {'member_id': self.esi.pk}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self._ministry_row(self.esi_user)['is_member'])

    def test_a_full_ministry_refuses_new_members(self):
        with tenant_context(self.church):
            Ministry.objects.filter(pk=self.choir.pk).update(max_capacity=1)
        self._client(self.esi_user).post(f'/api/v1/ministries/{self.choir.pk}/join/', {}, format='json')

        response = self._client(self.kofi_user).post(f'/api/v1/ministries/{self.choir.pk}/join/', {}, format='json')

        self.assertEqual(response.status_code, 400)

    def test_a_member_still_cannot_edit_a_ministry(self):
        response = self._client(self.kofi_user).patch(f'/api/v1/ministries/{self.choir.pk}/',
                                                      {'name': 'Mine now'}, format='json')

        self.assertEqual(response.status_code, 403)

    def test_a_login_without_a_member_record_cannot_join(self):
        response = self._client(self.unlinked_user).post(f'/api/v1/ministries/{self.choir.pk}/join/', {},
                                                         format='json')

        self.assertEqual(response.status_code, 400)

    # --- events ---

    def _upcoming_row(self, user):
        rows = self._client(user).get('/api/v1/events/upcoming/').data['data']
        return next(row for row in rows if row['id'] == self.event.pk)

    def test_a_member_rsvps_and_cancels_as_themselves(self):
        client = self._client(self.kofi_user)
        url = f'/api/v1/events/{self.event.pk}/'

        self.assertEqual(client.post(url + 'register/', {}, format='json').status_code, 200)
        row = self._upcoming_row(self.kofi_user)
        self.assertEqual((row['is_registered'], row['attendee_count']), (True, 1))
        self.assertFalse(self._upcoming_row(self.esi_user)['is_registered'])
        self.assertEqual(client.post(url + 'register/', {}, format='json').status_code, 400)  # no double RSVP

        self.assertEqual(client.delete(url + 'unregister/').status_code, 200)
        row = self._upcoming_row(self.kofi_user)
        self.assertEqual((row['is_registered'], row['attendee_count']), (False, 0))

    def test_a_member_cannot_rsvp_for_someone_else(self):
        self._client(self.kofi_user).post(f'/api/v1/events/{self.event.pk}/register/',
                                          {'member_id': self.esi.pk}, format='json')

        with tenant_context(self.church):
            registered = set(EventRegistration.objects.values_list('member_id', flat=True))
        self.assertEqual(registered, {self.kofi.pk})

    def test_a_full_event_refuses_more_rsvps(self):
        with tenant_context(self.church):
            Event.objects.filter(pk=self.event.pk).update(max_attendees=1)
        self._client(self.esi_user).post(f'/api/v1/events/{self.event.pk}/register/', {}, format='json')

        response = self._client(self.kofi_user).post(f'/api/v1/events/{self.event.pk}/register/', {},
                                                     format='json')

        self.assertEqual(response.status_code, 400)

    def test_only_staff_see_who_registered(self):
        self._client(self.esi_user).post(f'/api/v1/events/{self.event.pk}/register/', {}, format='json')
        member, admin = self._client(self.kofi_user), self._client(self.admin)
        url = f'/api/v1/events/{self.event.pk}/'

        self.assertEqual(member.get(url + 'attendees/').status_code, 403)
        self.assertNotIn('registrations', member.get(url).data)
        self.assertEqual(admin.get(url + 'attendees/').status_code, 200)
        self.assertEqual(len(admin.get(url).data['registrations']), 1)

    def test_a_member_still_cannot_create_or_edit_events(self):
        client = self._client(self.kofi_user)

        self.assertEqual(client.patch(f'/api/v1/events/{self.event.pk}/', {'title': 'x'},
                                      format='json').status_code, 403)
        self.assertEqual(client.post('/api/v1/events/', {'title': 'x'}, format='json').status_code, 403)
