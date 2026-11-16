"""
After a demo, a platform admin creates the church: it gets its own schema, a
trial, and one admin with no password who is emailed an invite link.
"""
from datetime import timedelta
from unittest import mock

from django.core import mail
from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.authentication.models import User
from apps.churches.models import Church
from apps.churches.subscriptions import TRIAL_DAYS
from apps.superadmin.models import DemoRequest

CREATE_URL = '/api/v1/platform/churches/'
FORM = {'church_name': 'Grace Chapel', 'subdomain': 'gracechapel', 'denomination': 'Methodist',
        'admin_name': 'Ama Owusu', 'admin_email': 'Ama@GraceChapel.example.test'}


def schema_exists(name):
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1 FROM information_schema.schemata WHERE schema_name = %s', [name])
        return cursor.fetchone() is not None


@override_settings(FRONTEND_URL='https://www.faithflow.example.test')
class CreateChurchTests(TestCase):
    def setUp(self):
        connection.set_schema_to_public()
        self.superadmin = User.objects.create_user(email='owner@platform.example.test', password='pass-12345',
                                                   name='Platform Owner', role='superadmin')
        self.client = APIClient()
        self.client.force_authenticate(user=self.superadmin)

    def tearDown(self):
        connection.set_schema_to_public()

    def create(self, **overrides):
        return self.client.post(CREATE_URL, {**FORM, **overrides}, format='json')

    def test_creates_the_church_on_a_trial_with_an_invited_admin(self):
        response = self.create()

        self.assertEqual(response.status_code, 201, response.content)
        church = Church.objects.get(subdomain='gracechapel')
        self.assertTrue(schema_exists('gracechapel'))
        self.assertEqual(church.plan, 'trial')
        self.assertAlmostEqual(church.trial_end_date, timezone.now() + timedelta(days=TRIAL_DAYS),
                               delta=timedelta(minutes=1))
        self.assertTrue(church.features.get('events'))
        admin = User.objects.get(email='ama@gracechapel.example.test')
        self.assertEqual((admin.church, admin.role), (church, 'admin'))
        self.assertFalse(admin.has_usable_password())
        self.assertFalse(admin.is_staff)
        self.assertTrue(response.data['invite_sent'])
        self.assertEqual(response.data['church']['account_state'], 'trial')

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['ama@gracechapel.example.test'])
        self.assertIn('https://gracechapel.faithflow.example.test/reset-password?token=', mail.outbox[0].body)

    def test_the_new_admin_can_set_a_password_from_the_invite(self):
        self.create()
        token = mail.outbox[0].body.split('token=')[1].split('&')[0]

        response = APIClient().post('/api/v1/auth/reset-password/', {'token': token,
                                                                     'new_password': 'Grace-Chapel-2026!'},
                                    format='json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.get(email='ama@gracechapel.example.test').check_password('Grace-Chapel-2026!'))

    def test_links_the_demo_request_and_moves_it_to_trial(self):
        demo_request = DemoRequest.objects.create(name='Ama Owusu', phone='+233 20 000 0000',
                                                  email='ama@gracechapel.example.test', church_name='Grace Chapel',
                                                  congregation_size='100_300', status='demo_booked')

        self.create(demo_request=demo_request.pk)

        demo_request.refresh_from_db()
        self.assertEqual(demo_request.status, 'trial')
        self.assertEqual(demo_request.church.subdomain, 'gracechapel')

    def test_bad_addresses_are_refused_before_anything_is_created(self):
        for subdomain in ('Grace Chapel', 'gc', '-grace', 'www', 'admin', 'grace_chapel'):
            response = self.create(subdomain=subdomain)
            self.assertEqual(response.status_code, 400, subdomain)
        self.assertFalse(Church.objects.exists())
        self.assertFalse(User.objects.filter(role='admin').exists())

    def test_an_address_in_use_is_refused(self):
        with mock.patch.object(Church, 'auto_create_schema', False):
            Church.objects.create(schema_name='gracechapel', subdomain='gracechapel', name='Existing',
                                  email='x@example.test')

        response = self.create()

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email__iexact=FORM['admin_email']).exists())

    def test_an_email_that_already_has_an_account_is_refused(self):
        response = self.create(admin_email='OWNER@platform.example.test')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Church.objects.filter(subdomain='gracechapel').exists())

    def test_resend_invite_goes_to_admins_who_never_signed_in(self):
        church_id = self.create().data['church']['id']
        mail.outbox.clear()

        response = self.client.post(f'{CREATE_URL}{church_id}/resend-invite/')

        self.assertEqual(response.data, {'sent': 1})
        self.assertEqual(len(mail.outbox), 1)

        User.objects.filter(email='ama@gracechapel.example.test').update(last_login=timezone.now())
        response = self.client.post(f'{CREATE_URL}{church_id}/resend-invite/')
        self.assertEqual(response.status_code, 400)

    def test_church_admins_cannot_create_churches(self):
        with mock.patch.object(Church, 'auto_create_schema', False):
            church = Church.objects.create(schema_name='otherchurch', subdomain='otherchurch', name='Other',
                                           email='o@example.test')
        church_admin = User.objects.create_user(email='admin@other.example.test', password='pass-12345',
                                                name='Admin', church=church, role='admin')
        client = APIClient()
        client.force_authenticate(user=church_admin)

        response = client.post(CREATE_URL, FORM, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Church.objects.filter(subdomain='gracechapel').exists())
