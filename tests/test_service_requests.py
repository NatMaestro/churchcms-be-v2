"""
Service requests (baptism, marriage, funeral, counselling, ...): a member
submits as themselves, sees only their own, and can cancel one while it is
pending; church staff see all of them with contact details and manage them.
"""
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
from apps.requests.models import ServiceRequest

SCHEMA = 'servicechurch'
URL = '/api/v1/service-requests/'


def results(response):
    data = response.data
    return data['results'] if isinstance(data, dict) and 'results' in data else data


class ServiceRequestTests(TransactionTestCase):
    # See tests/test_tenant_binding.py: makes the flush use TRUNCATE ... CASCADE.
    available_apps = list(settings.INSTALLED_APPS)

    def setUp(self):
        cache.clear()
        connection.set_schema_to_public()
        self.church = Church.objects.create(schema_name=SCHEMA, subdomain=SCHEMA, name='Service Church',
                                            email='office@service.example.test', bypass_subscription_check=True)
        self.admin = self._user('admin@service.example.test', 'admin')
        self.kofi_user = self._user('kofi@service.example.test', 'member')
        self.esi_user = self._user('esi@service.example.test', 'member')
        self.unlinked_user = self._user('new@service.example.test', 'member')
        with tenant_context(self.church):
            self.kofi = Member.objects.create(user=self.kofi_user, member_id='S-1', first_name='Kofi',
                                              last_name='Mensah', email='kofi@service.example.test',
                                              phone='0201111111')
            self.esi = Member.objects.create(user=self.esi_user, member_id='S-2', first_name='Esi',
                                             last_name='Owusu', email='esi@service.example.test')
            self.esi_request = ServiceRequest.objects.create(member=self.esi, type='baptism',
                                                             title='Baptism for Ama', description='My daughter.')

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

    def _submit(self, user, **fields):
        data = {'type': 'visitation', 'title': 'Hospital visit', 'description': 'My father is at Korle Bu.', **fields}
        return self._client(user).post(URL, data, format='json')

    # --- submitting ---

    def test_a_member_submits_a_request_as_themselves(self):
        response = self._submit(self.kofi_user, member=self.esi.pk, status='approved', admin_notes='forged',
                                priority='urgent', request_data={'preferred_date': '2026-12-07', 'extra': 'x'})

        self.assertEqual(response.status_code, 201, response.content)
        with tenant_context(self.church):
            saved = ServiceRequest.objects.get(pk=response.data['id'])
        self.assertEqual((saved.member_id, saved.status, saved.admin_notes, saved.priority),
                         (self.kofi.pk, 'pending', '', 'urgent'))
        self.assertEqual(saved.request_data, {'preferred_date': '2026-12-07'})

    def test_a_bad_preferred_date_is_refused(self):
        response = self._submit(self.kofi_user, request_data={'preferred_date': 'next week'})

        self.assertEqual(response.status_code, 400)

    def test_a_login_without_a_member_record_cannot_submit(self):
        self.assertEqual(self._submit(self.unlinked_user).status_code, 400)

    def test_the_churchs_admins_are_notified(self):
        self._submit(self.kofi_user)

        with tenant_context(self.church):
            notified = set(Notification.objects.values_list('user_id', 'title'))
        self.assertIn((self.admin.pk, 'New Service Request'), notified)

    # --- what a member sees ---

    def test_a_member_sees_only_their_own_requests(self):
        self._submit(self.kofi_user)
        client = self._client(self.kofi_user)

        self.assertEqual([row['title'] for row in results(client.get(URL))], ['Hospital visit'])
        self.assertEqual(client.get(f'{URL}{self.esi_request.pk}/').status_code, 404)

    def test_a_member_sees_the_churchs_reply_but_no_contact_details(self):
        request_id = self._submit(self.kofi_user).data['id']
        self._client(self.admin).patch(f'{URL}{request_id}/', {'status': 'approved',
                                                              'admin_notes': 'Pastor visits Thursday.'}, format='json')

        detail = self._client(self.kofi_user).get(f'{URL}{request_id}/').data

        self.assertEqual((detail['status'], detail['admin_notes']), ('approved', 'Pastor visits Thursday.'))
        self.assertNotIn('member_phone', detail)
        self.assertNotIn('member_email', detail)

    # --- changing requests ---

    def test_a_member_cannot_edit_delete_or_approve_requests(self):
        request_id = self._submit(self.kofi_user).data['id']
        client = self._client(self.kofi_user)
        url = f'{URL}{request_id}/'

        self.assertEqual(client.patch(url, {'status': 'completed'}, format='json').status_code, 403)
        self.assertEqual(client.delete(url).status_code, 403)
        for action in ('approve', 'reject', 'complete'):
            self.assertEqual(client.post(f'{url}{action}/').status_code, 403, action)
        with tenant_context(self.church):
            self.assertEqual(ServiceRequest.objects.get(pk=request_id).status, 'pending')

    def test_a_member_cancels_their_own_pending_request(self):
        request_id = self._submit(self.kofi_user).data['id']

        response = self._client(self.kofi_user).post(f'{URL}{request_id}/cancel/')

        self.assertEqual((response.status_code, response.data['status']), (200, 'cancelled'))

    def test_a_request_the_church_has_acted_on_cannot_be_cancelled(self):
        request_id = self._submit(self.kofi_user).data['id']
        self._client(self.admin).post(f'{URL}{request_id}/approve/')

        self.assertEqual(self._client(self.kofi_user).post(f'{URL}{request_id}/cancel/').status_code, 400)

    def test_a_member_cannot_cancel_someone_elses_request(self):
        self.assertEqual(self._client(self.kofi_user).post(f'{URL}{self.esi_request.pk}/cancel/').status_code, 404)

    # --- church staff ---

    def test_staff_see_every_request_with_contact_details(self):
        self._submit(self.kofi_user)
        client = self._client(self.admin)

        rows = results(client.get(URL))
        self.assertEqual(len(rows), 2)
        mine = next(row for row in rows if row['title'] == 'Hospital visit')
        detail = client.get(f'{URL}{mine["id"]}/').data
        self.assertEqual((detail['member_phone'], detail['member_email']), ('0201111111', 'kofi@service.example.test'))

    def test_staff_marking_a_request_completed_records_when(self):
        response = self._client(self.admin).patch(f'{URL}{self.esi_request.pk}/', {'status': 'completed'},
                                                  format='json')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNotNone(response.data['completed_at'])
