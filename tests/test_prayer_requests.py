"""
Prayer requests: a member submits requests as themselves, sees their own plus
those other members chose to share, prays for shared ones, and changes only
their own. Church staff see and manage all of them, with contact details.
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
from apps.prayers.models import PrayerRequest

SCHEMA = 'prayerchurch'
URL = '/api/v1/prayer-requests/'


def results(response):
    data = response.data
    return data['results'] if isinstance(data, dict) and 'results' in data else data


class PrayerRequestTests(TransactionTestCase):
    # See tests/test_tenant_binding.py: makes the flush use TRUNCATE ... CASCADE.
    available_apps = list(settings.INSTALLED_APPS)

    def setUp(self):
        cache.clear()
        connection.set_schema_to_public()
        self.church = Church.objects.create(schema_name=SCHEMA, subdomain=SCHEMA, name='Prayer Church',
                                            email='office@prayer.example.test', bypass_subscription_check=True)
        self.admin = self._user('admin@prayer.example.test', 'admin')
        self.kofi_user = self._user('kofi@prayer.example.test', 'member')
        self.esi_user = self._user('esi@prayer.example.test', 'member')
        self.unlinked_user = self._user('new@prayer.example.test', 'member')
        with tenant_context(self.church):
            self.kofi = Member.objects.create(user=self.kofi_user, member_id='P-1', first_name='Kofi',
                                              last_name='Mensah', email='kofi@prayer.example.test')
            self.esi = Member.objects.create(user=self.esi_user, member_id='P-2', first_name='Esi',
                                             last_name='Owusu', email='esi@prayer.example.test')
            self.esi_shared = PrayerRequest.objects.create(
                member=self.esi, title='Exams', description='Pray for my exams.', category='guidance',
                is_public=True, requester_email='esi@prayer.example.test', requester_phone='0200000002')
            self.esi_private = PrayerRequest.objects.create(
                member=self.esi, title='Private', description='Just for the pastors.', category='family',
                is_public=False)
            self.esi_confidential = PrayerRequest.objects.create(
                member=self.esi, title='Confidential', description='Sensitive.', category='other',
                is_public=True, is_confidential=True)

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
        data = {'title': 'Healing', 'description': 'Pray for my mother.', 'category': 'healing', **fields}
        return self._client(user).post(URL, data, format='json')

    # --- submitting ---

    def test_a_member_submits_a_request_as_themselves(self):
        response = self._submit(self.kofi_user, member=self.esi.pk, status='answered', is_public=True)

        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(response.data['is_mine'])
        with tenant_context(self.church):
            saved = PrayerRequest.objects.get(pk=response.data['id'])
        self.assertEqual((saved.member_id, saved.status, saved.is_public), (self.kofi.pk, 'active', True))

    def test_a_confidential_request_is_never_shared(self):
        response = self._submit(self.kofi_user, is_public=True, is_confidential=True)

        self.assertEqual(response.status_code, 201, response.content)
        self.assertFalse(response.data['is_public'])

    def test_a_login_without_a_member_record_cannot_submit(self):
        self.assertEqual(self._submit(self.unlinked_user).status_code, 400)

    def test_the_churchs_admins_are_notified_of_a_new_request(self):
        self._submit(self.kofi_user)

        with tenant_context(self.church):
            notified = set(Notification.objects.values_list('user_id', 'title'))
        self.assertIn((self.admin.pk, 'New Prayer Request'), notified)

    # --- what a member sees ---

    def test_a_member_sees_their_own_and_shared_requests_only(self):
        self._submit(self.kofi_user, title='Mine, private')

        titles = {row['title'] for row in results(self._client(self.kofi_user).get(URL))}

        self.assertEqual(titles, {'Mine, private', 'Exams'})

    def test_a_member_never_sees_contact_details(self):
        client = self._client(self.kofi_user)
        row = results(client.get(URL))[0]
        detail = client.get(f'{URL}{self.esi_shared.pk}/').data

        for data in (row, detail):
            self.assertNotIn('requester_email', data)
            self.assertNotIn('requester_phone', data)
        self.assertEqual(detail['requester'], 'Esi Owusu')

    def test_a_member_cannot_open_someone_elses_private_request(self):
        client = self._client(self.kofi_user)

        self.assertEqual(client.get(f'{URL}{self.esi_private.pk}/').status_code, 404)
        self.assertEqual(client.get(f'{URL}{self.esi_confidential.pk}/').status_code, 404)

    # --- changing requests ---

    def test_a_member_cannot_change_or_delete_someone_elses_shared_request(self):
        client = self._client(self.kofi_user)
        url = f'{URL}{self.esi_shared.pk}/'

        self.assertEqual(client.patch(url, {'title': 'Changed'}, format='json').status_code, 404)
        self.assertEqual(client.delete(url).status_code, 404)
        self.assertEqual(client.patch(url + 'mark_answered/', {}, format='json').status_code, 404)
        with tenant_context(self.church):
            self.assertEqual(PrayerRequest.objects.get(pk=self.esi_shared.pk).title, 'Exams')

    def test_a_member_edits_and_withdraws_their_own_request(self):
        client = self._client(self.kofi_user)
        request_id = self._submit(self.kofi_user).data['id']

        response = client.patch(f'{URL}{request_id}/', {'title': 'Updated', 'status': 'completed'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual((response.data['title'], response.data['status']), ('Updated', 'active'))

        self.assertEqual(client.delete(f'{URL}{request_id}/').status_code, 204)

    def test_a_member_marks_their_own_request_answered(self):
        client = self._client(self.kofi_user)
        request_id = self._submit(self.kofi_user).data['id']

        response = client.patch(f'{URL}{request_id}/mark_answered/', {'testimony': 'She recovered.'}, format='json')

        self.assertEqual(response.status_code, 200)
        with tenant_context(self.church):
            saved = PrayerRequest.objects.get(pk=request_id)
        self.assertEqual((saved.status, saved.answer_testimony), ('answered', 'She recovered.'))

    # --- praying ---

    def test_praying_counts_each_member_once(self):
        kofi, admin_view = self._client(self.kofi_user), self._client(self.admin)
        url = f'{URL}{self.esi_shared.pk}/pray/'

        first = kofi.post(url)
        second = kofi.post(url)

        self.assertEqual((first.status_code, first.data['prayer_count']), (200, 1))
        self.assertEqual(second.data['prayer_count'], 1)
        row = next(r for r in results(kofi.get(URL)) if r['id'] == self.esi_shared.pk)
        self.assertEqual((row['prayer_count'], row['i_prayed']), (1, True))
        esi_row = next(r for r in results(self._client(self.esi_user).get(URL)) if r['id'] == self.esi_shared.pk)
        self.assertFalse(esi_row['i_prayed'])
        self.assertEqual(admin_view.get(f'{URL}{self.esi_shared.pk}/').data['prayer_count'], 1)

    def test_a_member_cannot_pray_on_a_request_they_cannot_see(self):
        self.assertEqual(self._client(self.kofi_user).post(f'{URL}{self.esi_private.pk}/pray/').status_code, 404)

    # --- church staff ---

    def test_staff_see_every_request_with_contact_details(self):
        client = self._client(self.admin)

        self.assertEqual(len(results(client.get(URL))), 3)
        detail = client.get(f'{URL}{self.esi_shared.pk}/').data
        self.assertEqual((detail['requester_email'], detail['requester_phone']),
                         ('esi@prayer.example.test', '0200000002'))

    def test_staff_can_reach_a_member_who_asked_through_the_portal(self):
        with tenant_context(self.church):
            Member.objects.filter(pk=self.kofi.pk).update(phone='0201111111')
        request_id = self._submit(self.kofi_user).data['id']

        detail = self._client(self.admin).get(f'{URL}{request_id}/').data

        self.assertEqual((detail['member_phone'], detail['member_email']), ('0201111111', 'kofi@prayer.example.test'))

    def test_staff_update_the_status_and_answer(self):
        response = self._client(self.admin).patch(f'{URL}{self.esi_private.pk}/', {
            'status': 'praying', 'answer_testimony': 'The prayer team is praying with you.',
        }, format='json')

        self.assertEqual(response.status_code, 200, response.content)
        member_view = self._client(self.esi_user).get(f'{URL}{self.esi_private.pk}/').data
        self.assertEqual(member_view['status'], 'praying')
        self.assertEqual(member_view['answer_testimony'], 'The prayer team is praying with you.')
