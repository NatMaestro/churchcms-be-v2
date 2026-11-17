"""
Altar calls: church staff record who came forward (a member, or a visitor by
name and phone) and track follow-up. Members never see altar-call records.
"""
from datetime import date

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.test import TransactionTestCase
from django_tenants.utils import tenant_context
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.altarcalls.models import AltarCall
from apps.authentication.models import User
from apps.churches.models import Church
from apps.members.models import Member

SCHEMA = 'altarchurch'
URL = '/api/v1/altar-calls/'


def results(response):
    data = response.data
    return data['results'] if isinstance(data, dict) and 'results' in data else data


class AltarCallTests(TransactionTestCase):
    # See tests/test_tenant_binding.py: makes the flush use TRUNCATE ... CASCADE.
    available_apps = list(settings.INSTALLED_APPS)

    def setUp(self):
        cache.clear()
        connection.set_schema_to_public()
        self.church = Church.objects.create(schema_name=SCHEMA, subdomain=SCHEMA, name='Altar Church',
                                            email='office@altar.example.test', bypass_subscription_check=True)
        self.admin = User.objects.create_user(email='admin@altar.example.test', password='pass-12345',
                                              name='Pastor', church=self.church, role='admin')
        self.member_user = User.objects.create_user(email='kofi@altar.example.test', password='pass-12345',
                                                    name='Kofi', church=self.church, role='member')
        with tenant_context(self.church):
            self.kofi = Member.objects.create(user=self.member_user, member_id='A-1', first_name='Kofi',
                                              last_name='Mensah', phone='0201111111')
            AltarCall.objects.create(member=self.kofi, service_date=date(2026, 11, 15),
                                     service_type='sunday_service', reason='rededication',
                                     follow_up_notes='Pastoral note.')

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

    def _record(self, **fields):
        data = {'service_date': '2026-11-15', 'service_type': 'sunday_service', 'reason': 'salvation', **fields}
        return self._client(self.admin).post(URL, data, format='json')

    def test_staff_record_a_visitor_who_came_forward(self):
        response = self._record(visitor_name='  Abena Owusu ', visitor_phone='0249999999')

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual((response.data['person_name'], response.data['visitor_phone']),
                         ('Abena Owusu', '0249999999'))
        self.assertEqual(response.data['follow_up_status'], 'pending')

    def test_staff_record_a_member_and_any_visitor_details_are_dropped(self):
        response = self._record(member=self.kofi.pk, visitor_name='Someone else', visitor_phone='0200000000')

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual((response.data['person_name'], response.data['member_phone']), ('Kofi Mensah', '0201111111'))
        self.assertEqual((response.data['visitor_name'], response.data['visitor_phone']), ('', ''))

    def test_a_record_needs_a_member_or_a_visitor_name(self):
        response = self._record(visitor_phone='0249999999')

        self.assertEqual(response.status_code, 400)

    def test_staff_track_follow_up(self):
        record_id = self._record(visitor_name='Abena').data['id']

        response = self._client(self.admin).patch(f'{URL}{record_id}/', {
            'follow_up_status': 'completed', 'follow_up_notes': 'Visited at home; joining new believers class.',
        }, format='json')

        self.assertEqual(response.status_code, 200, response.content)
        pending = self._client(self.admin).get(f'{URL}follow_up_pending/').data['data']
        self.assertNotIn(record_id, [row['id'] for row in pending])

    def test_members_cannot_see_or_record_altar_calls(self):
        client = self._client(self.member_user)

        self.assertEqual(client.get(URL).status_code, 403)
        self.assertEqual(client.post(URL, {'visitor_name': 'X', 'service_date': '2026-11-15',
                                           'service_type': 'other', 'reason': 'other'}, format='json').status_code,
                         403)
        self.assertEqual(client.get(f'{URL}follow_up_pending/').status_code, 403)

    def test_staff_list_shows_who_came_forward(self):
        self._record(visitor_name='Abena')

        names = {row['person_name'] for row in results(self._client(self.admin).get(URL))}

        self.assertEqual(names, {'Kofi Mensah', 'Abena'})
