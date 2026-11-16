"""
"Book a demo": anyone can ask, only platform superadmins can see the details,
the notification email carries no contact details, and stale leads are purged.
"""
from datetime import timedelta
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.authentication.models import User
from apps.churches.models import Church
from apps.superadmin.models import STALE_DEMO_REQUEST_DAYS, DemoRequest

SUBMIT_URL = '/api/v1/demo-requests/'
PLATFORM_URL = '/api/v1/platform/demo-requests/'
FORM = {
    'name': '  Rev. Kofi Mensah ', 'role': 'Pastor', 'phone': '+233 24 000 0000',
    'email': 'kofi@gracechapel.example.test', 'church_name': 'Grace Chapel',
    'congregation_size': '100_300', 'preferred_time': 'Weekday evenings',
    'message': 'We want to track tithes and members.',
}


class DemoRequestTestCase(TestCase):
    def setUp(self):
        connection.set_schema_to_public()
        cache.clear()  # throttle counters
        self.superadmin = User.objects.create_user(email='owner@platform.example.test', password='pass-12345',
                                                   name='Platform Owner', role='superadmin')

    def submit(self, **overrides):
        return APIClient().post(SUBMIT_URL, {**FORM, **overrides}, format='json')

    def make_request(self, **fields):
        data = {key: value.strip() for key, value in FORM.items()}
        data.update(fields)
        return DemoRequest.objects.create(**data)


class SubmitTests(DemoRequestTestCase):
    def test_anyone_can_book_a_demo(self):
        response = self.submit()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.data), {'success', 'message'})
        saved = DemoRequest.objects.get()
        self.assertEqual(saved.name, 'Rev. Kofi Mensah')
        self.assertEqual(saved.status, 'new')

    def test_platform_admins_are_emailed_without_contact_details(self):
        self.submit()

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['owner@platform.example.test'])
        self.assertIn('Grace Chapel', email.subject)
        for private in ('+233 24 000 0000', 'kofi@gracechapel.example.test', 'track tithes'):
            self.assertNotIn(private, email.body)

    def test_required_fields_are_checked(self):
        response = self.submit(phone='', congregation_size='enormous')

        self.assertEqual(response.status_code, 400)
        self.assertIn('phone', response.data['errors'])
        self.assertIn('congregation_size', response.data['errors'])
        self.assertFalse(DemoRequest.objects.exists())

    def test_bots_filling_the_hidden_field_are_ignored(self):
        response = self.submit(website='http://spam.example.test')

        self.assertEqual(response.status_code, 201)
        self.assertFalse(DemoRequest.objects.exists())
        self.assertEqual(mail.outbox, [])

    def test_submissions_are_rate_limited(self):
        statuses = [self.submit(email=f'person{i}@example.test').status_code for i in range(6)]

        self.assertEqual(statuses[:5], [201] * 5)
        self.assertEqual(statuses[5], 429)


class RetentionTests(DemoRequestTestCase):
    def age(self, demo_request, days):
        DemoRequest.objects.filter(pk=demo_request.pk).update(updated_at=timezone.now() - timedelta(days=days))

    def test_leads_that_went_nowhere_for_a_year_are_deleted(self):
        stale_lost = self.make_request(status='lost')
        stale_new = self.make_request(status='new')
        stale_trial = self.make_request(status='trial')
        recent = self.make_request(status='contacted')
        for demo_request in (stale_lost, stale_new, stale_trial):
            self.age(demo_request, STALE_DEMO_REQUEST_DAYS + 1)

        self.submit()

        remaining = set(DemoRequest.objects.values_list('pk', flat=True))
        self.assertNotIn(stale_lost.pk, remaining)
        self.assertNotIn(stale_new.pk, remaining)
        self.assertIn(stale_trial.pk, remaining)
        self.assertIn(recent.pk, remaining)


class PlatformAccessTests(DemoRequestTestCase):
    def setUp(self):
        super().setUp()
        self.demo_request = self.make_request()
        self.client = APIClient()
        self.client.force_authenticate(user=self.superadmin)

    def test_superadmin_sees_and_follows_up_on_requests(self):
        listed = self.client.get(PLATFORM_URL, {'status': 'new'}).data['results']
        self.assertEqual([item['phone'] for item in listed], ['+233 24 000 0000'])

        response = self.client.patch(f'{PLATFORM_URL}{self.demo_request.pk}/', {
            'status': 'demo_booked', 'notes': 'Thursday 6pm on WhatsApp video', 'name': 'Someone Else',
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.demo_request.refresh_from_db()
        self.assertEqual(self.demo_request.status, 'demo_booked')
        self.assertEqual(self.demo_request.notes, 'Thursday 6pm on WhatsApp video')
        self.assertEqual(self.demo_request.name, 'Rev. Kofi Mensah')

    def test_superadmin_can_delete_a_request(self):
        response = self.client.delete(f'{PLATFORM_URL}{self.demo_request.pk}/')

        self.assertEqual(response.status_code, 204)
        self.assertFalse(DemoRequest.objects.exists())

    def test_every_read_is_logged_without_personal_data(self):
        with self.assertLogs('apps.superadmin.views', level='INFO') as logs:
            self.client.get(PLATFORM_URL)
            self.client.get(f'{PLATFORM_URL}{self.demo_request.pk}/')

        actions = [record.action for record in logs.records]
        self.assertEqual(actions, ['list_demo_requests', 'view_demo_request'])
        self.assertTrue(all(record.actor_id == self.superadmin.pk for record in logs.records))
        self.assertNotIn('+233', ' '.join(logs.output))

    def test_church_admins_and_visitors_cannot_see_requests(self):
        with mock.patch.object(Church, 'auto_create_schema', False):
            church = Church.objects.create(schema_name='demochurch', subdomain='demochurch', name='Demo',
                                           email='office@demochurch.example.test')
        church_admin = User.objects.create_user(email='admin@demochurch.example.test', password='pass-12345',
                                                name='Admin', church=church, role='admin')
        client = APIClient()
        client.force_authenticate(user=church_admin)

        self.assertEqual(client.get(PLATFORM_URL).status_code, 403)
        self.assertIn(APIClient().get(PLATFORM_URL).status_code, (401, 403))
