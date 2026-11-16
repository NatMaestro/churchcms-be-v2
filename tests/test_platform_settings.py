"""
Platform settings: a platform superadmin sets the WhatsApp number and contact
email; the website reads them publicly; nobody else can change them.
"""
from unittest import mock

from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient

from apps.authentication.models import User
from apps.churches.models import Church
from apps.superadmin.models import PlatformSettings

PUBLIC_URL = '/api/v1/site-settings/'
ADMIN_URL = '/api/v1/platform/settings/'


class PlatformSettingsTests(TestCase):
    def setUp(self):
        connection.set_schema_to_public()
        self.superadmin = User.objects.create_user(email='owner@platform.example.test', password='pass-12345',
                                                   name='Platform Owner', role='superadmin')
        self.client = APIClient()
        self.client.force_authenticate(user=self.superadmin)

    def save(self, **data):
        return self.client.patch(ADMIN_URL, data, format='json')

    def test_empty_until_set(self):
        response = APIClient().get(PUBLIC_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'version': 1, 'whatsapp_number': '', 'contact_email': ''})

    def test_superadmin_sets_contacts_and_the_website_shows_them(self):
        response = self.save(whatsapp_number='+233 20 123 4567', contact_email='hello@faithflow.example.test')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data['whatsapp_number'], '233201234567')
        self.assertEqual(response.data['updated_by_name'], 'Platform Owner')
        public = APIClient().get(PUBLIC_URL).data
        self.assertEqual(public['whatsapp_number'], '233201234567')
        self.assertEqual(public['contact_email'], 'hello@faithflow.example.test')

    def test_clearing_a_field_hides_it(self):
        self.save(whatsapp_number='233201234567')

        self.save(whatsapp_number='')

        self.assertEqual(APIClient().get(PUBLIC_URL).data['whatsapp_number'], '')

    def test_invalid_values_are_refused(self):
        for data in ({'whatsapp_number': '0201234567'}, {'whatsapp_number': '12'},
                     {'whatsapp_number': 'call me'}, {'contact_email': 'not-an-email'}):
            response = self.save(**data)
            self.assertEqual(response.status_code, 400, data)
        self.assertEqual(PlatformSettings.load().whatsapp_number, '')

    def test_there_is_only_ever_one_settings_row(self):
        self.save(contact_email='a@example.test')
        self.save(contact_email='b@example.test')

        self.assertEqual(PlatformSettings.objects.count(), 1)

    def test_changes_are_logged_with_the_admin(self):
        with self.assertLogs('apps.superadmin.views', level='INFO') as logs:
            self.save(contact_email='a@example.test')

        record = logs.records[0]
        self.assertEqual((record.action, record.actor_id), ('update_platform_settings', self.superadmin.pk))

    def test_church_admins_and_visitors_cannot_change_them(self):
        with mock.patch.object(Church, 'auto_create_schema', False):
            church = Church.objects.create(schema_name='settingschurch', subdomain='settingschurch', name='S',
                                           email='s@example.test')
        church_admin = User.objects.create_user(email='admin@settings.example.test', password='pass-12345',
                                                name='Admin', church=church, role='admin')
        client = APIClient()
        client.force_authenticate(user=church_admin)

        self.assertEqual(client.patch(ADMIN_URL, {'contact_email': 'x@example.test'}, format='json').status_code, 403)
        self.assertIn(APIClient().patch(ADMIN_URL, {'contact_email': 'x@example.test'}, format='json').status_code,
                      (401, 403))
        self.assertEqual(PlatformSettings.load().contact_email, '')
