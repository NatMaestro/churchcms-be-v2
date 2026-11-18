"""
A new membership application alerts that church's admins; confirming it
creates the member's login and emails them a single-use invite link to set
their own password. Runs against real tenant schemas and Django's in-memory
mailbox, so nothing leaves the machine.
"""
import hashlib
import re
from datetime import timedelta
from smtplib import SMTPException
from unittest import mock

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.db import connection
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from django_tenants.utils import tenant_context
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import PasswordResetToken, User
from apps.churches.models import Church
from apps.members.models import Member, MemberRequest
from apps.notifications.models import Notification

SUBMIT_URL = '/api/v1/members/member-requests/submit/'
RESET_URL = '/api/v1/auth/reset-password/'
LIST_URL = '/api/v1/members/requests/'
TEST_SCHEMAS = ('invitea', 'inviteb')
SEND_MAIL = 'apps.members.member_request_notifications.send_mail'
APPLICANT_EMAIL = 'ama@example.test'
APPLICANT_PHONE = '0209998887'
APPLICANT_ADDRESS = '7 Private Lane'
NEW_PASSWORD = 'chosen-by-member-123'
MAIN_SITE = 'https://www.faithflow.example.test'
CHURCH_A_SITE = 'https://invitea.faithflow.example.test'
FORGOT_URL = '/api/v1/auth/forgot-password/'


def application_fields(**overrides):
    data = {
        'name': 'Ama Mensah',
        'email': APPLICANT_EMAIL,
        'phone': APPLICANT_PHONE,
        'address': APPLICANT_ADDRESS,
        'date_of_birth': '1990-05-17',
        'gender': 'Female',
        'marital_status': 'single',
        'church_experience': 'Grew up in church',
        'reason_for_joining': 'Community',
        'how_did_you_hear': 'A friend',
        'emergency_contact': {},
        'skills': [],
        'interests': [],
    }
    data.update(overrides)
    return data


def confirm_url(request_id):
    return f'/api/v1/members/requests/{request_id}/confirm/'


def resend_url(request_id):
    return f'/api/v1/members/requests/{request_id}/resend-invite/'


def token_from(email_message):
    return re.search(r'token=([\w-]+)', email_message.body).group(1)


@override_settings(FRONTEND_URL=MAIN_SITE)
class MemberInviteTests(TransactionTestCase):
    # See tests/test_tenant_binding.py: makes the flush use TRUNCATE ... CASCADE.
    available_apps = list(settings.INSTALLED_APPS)

    def setUp(self):
        cache.clear()  # throttle history lives in the cache
        connection.set_schema_to_public()
        self.church_a = self._make_church(TEST_SCHEMAS[0])
        self.church_b = self._make_church(TEST_SCHEMAS[1])
        self.admin_a = self._make_user('admin@invite-a.test', self.church_a, 'admin')
        self.admin_b = self._make_user('admin@invite-b.test', self.church_b, 'admin')
        self.member_a = self._make_user('member@invite-a.test', self.church_a, 'member')
        mail.outbox = []

    def tearDown(self):
        cache.clear()
        connection.set_schema_to_public()
        with connection.cursor() as cursor:
            for schema in TEST_SCHEMAS:
                cursor.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')

    @staticmethod
    def _make_church(subdomain):
        return Church.objects.create(
            schema_name=subdomain, subdomain=subdomain, name=subdomain.title(),
            email=f'office@{subdomain}.example.test', bypass_subscription_check=True,
        )

    @staticmethod
    def _make_user(email, church, role):
        return User.objects.create_user(
            email=email, password='pass-12345', name=email.split('@')[0], church=church, role=role,
        )

    @staticmethod
    def _client(user, subdomain):
        client = APIClient()
        token = RefreshToken.for_user(user).access_token
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}', HTTP_X_TENANT_SUBDOMAIN=subdomain)
        return client

    def _approved_request(self, church, **overrides):
        with tenant_context(church):
            return MemberRequest.objects.create(
                church=church, status='approved', **application_fields(**overrides),
            )

    def _confirm(self, member_request, admin=None, subdomain='invitea'):
        client = self._client(admin or self.admin_a, subdomain)
        return client.post(confirm_url(member_request.pk), format='json')

    def _notifications_in(self, church):
        with tenant_context(church):
            return list(Notification.objects.values_list('user_id', 'type'))

    # --- admin list of requests ---

    def test_admin_lists_only_their_churchs_requests(self):
        self._approved_request(self.church_a)
        self._approved_request(self.church_b, email='someone-else@example.test')

        response = self._client(self.admin_a, 'invitea').get(LIST_URL)

        self.assertEqual(response.status_code, 200)
        self.assertIn(APPLICANT_EMAIL, response.content.decode())
        self.assertNotIn('someone-else@example.test', response.content.decode())

    # --- admin alerts on a new application ---

    def test_new_application_alerts_only_that_churchs_admins(self):
        response = APIClient().post(
            SUBMIT_URL, {'subdomain': 'invitea', **application_fields()}, format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self._notifications_in(self.church_a), [(self.admin_a.pk, 'member_request')])
        self.assertEqual(self._notifications_in(self.church_b), [])
        self.assertEqual([m.to for m in mail.outbox], [[self.admin_a.email]])

    def test_admin_email_names_the_applicant_but_not_their_details(self):
        APIClient().post(SUBMIT_URL, {'subdomain': 'invitea', **application_fields()}, format='json')

        body = mail.outbox[0].body
        self.assertIn('Ama Mensah', body)
        for private in (APPLICANT_EMAIL, APPLICANT_PHONE, APPLICANT_ADDRESS):
            self.assertNotIn(private, body)

    def test_repeat_application_sends_no_alerts(self):
        client = APIClient()
        client.post(SUBMIT_URL, {'subdomain': 'invitea', **application_fields()}, format='json')
        mail.outbox = []

        client.post(SUBMIT_URL, {'subdomain': 'invitea', **application_fields()}, format='json')

        self.assertEqual(mail.outbox, [])
        self.assertEqual(len(self._notifications_in(self.church_a)), 1)

    def test_application_is_kept_when_admin_email_fails(self):
        with mock.patch(SEND_MAIL, side_effect=SMTPException('down')):
            response = APIClient().post(
                SUBMIT_URL, {'subdomain': 'invitea', **application_fields()}, format='json',
            )

        self.assertEqual(response.status_code, 201)
        with tenant_context(self.church_a):
            self.assertEqual(MemberRequest.objects.count(), 1)
        self.assertEqual(len(self._notifications_in(self.church_a)), 1)

    # --- invite on confirm ---

    def test_confirm_creates_login_without_password_and_emails_one_invite(self):
        member_request = self._approved_request(self.church_a)

        response = self._confirm(member_request)

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['data']['invite_sent'])
        user = User.objects.get(email=APPLICANT_EMAIL)
        self.assertFalse(user.has_usable_password())
        self.assertEqual([m.to for m in mail.outbox], [[APPLICANT_EMAIL]])
        self.assertIn('/reset-password?token=', mail.outbox[0].body)

    def test_invite_link_expires_after_72_hours(self):
        self._confirm(self._approved_request(self.church_a))

        token = PasswordResetToken.objects.get(token=hashlib.sha256(token_from(mail.outbox[0]).encode()).hexdigest())
        lifetime = token.expires_at - timezone.now()
        self.assertGreater(lifetime, timedelta(hours=71))
        self.assertLessEqual(lifetime, timedelta(hours=72))

    def test_invite_link_sets_password_once(self):
        self._confirm(self._approved_request(self.church_a))
        token = token_from(mail.outbox[0])

        first = APIClient().post(RESET_URL, {'token': token, 'new_password': NEW_PASSWORD}, format='json')
        second = APIClient().post(RESET_URL, {'token': token, 'new_password': 'another-pass-456'}, format='json')

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)
        user = User.objects.get(email=APPLICANT_EMAIL)
        self.assertTrue(user.check_password(NEW_PASSWORD))
        self.assertFalse(user.must_change_password)

    def test_confirm_reports_invite_not_sent_when_email_fails(self):
        member_request = self._approved_request(self.church_a)

        with mock.patch(SEND_MAIL, side_effect=SMTPException('down')):
            response = self._confirm(member_request)

        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()['data']['invite_sent'])
        self.assertTrue(User.objects.filter(email=APPLICANT_EMAIL).exists())

    def test_confirm_refuses_email_that_already_has_an_account(self):
        member_request = self._approved_request(self.church_a, email='Member@invite-a.test')

        response = self._confirm(member_request)

        self.assertEqual(response.status_code, 409)
        self.assertNotIn('Traceback', response.content.decode())
        with tenant_context(self.church_a):
            self.assertEqual(Member.objects.count(), 0)
        self.assertEqual(mail.outbox, [])

    # --- links open on the church's own site ---

    def test_admin_alert_links_to_the_churchs_site(self):
        APIClient().post(SUBMIT_URL, {'subdomain': 'invitea', **application_fields()}, format='json')

        self.assertIn(f'{CHURCH_A_SITE}/admin/member-requests', mail.outbox[0].body)

    def test_invite_link_opens_on_the_churchs_site(self):
        self._confirm(self._approved_request(self.church_a))

        self.assertIn(f'{CHURCH_A_SITE}/reset-password?token=', mail.outbox[0].body)

    def test_member_reset_link_opens_on_the_churchs_site(self):
        APIClient().post(FORGOT_URL, {'email': self.member_a.email}, format='json')

        self.assertIn(f'{CHURCH_A_SITE}/reset-password?token=', mail.outbox[0].body)

    def test_reset_link_for_user_without_church_uses_the_main_site(self):
        User.objects.create_user(email='platform@example.test', password='pass-12345',
                                 name='Platform', role='superadmin')

        APIClient().post(FORGOT_URL, {'email': 'platform@example.test'}, format='json')

        self.assertIn(f'{MAIN_SITE}/reset-password?token=', mail.outbox[0].body)

    # --- resend invite ---

    def test_resend_invite_replaces_the_old_link(self):
        member_request = self._approved_request(self.church_a)
        self._confirm(member_request)
        old_token = token_from(mail.outbox[0])

        response = self._client(self.admin_a, 'invitea').post(resend_url(member_request.pk))

        self.assertEqual(response.status_code, 200)
        new_token = token_from(mail.outbox[1])
        old = APIClient().post(RESET_URL, {'token': old_token, 'new_password': NEW_PASSWORD}, format='json')
        new = APIClient().post(RESET_URL, {'token': new_token, 'new_password': NEW_PASSWORD}, format='json')
        self.assertEqual(old.status_code, 400)
        self.assertEqual(new.status_code, 200)

    def test_resend_invite_refused_once_password_is_set(self):
        member_request = self._approved_request(self.church_a)
        self._confirm(member_request)
        APIClient().post(
            RESET_URL, {'token': token_from(mail.outbox[0]), 'new_password': NEW_PASSWORD}, format='json',
        )

        response = self._client(self.admin_a, 'invitea').post(resend_url(member_request.pk))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_invite_refused_for_unconfirmed_request(self):
        member_request = self._approved_request(self.church_a)

        response = self._client(self.admin_a, 'invitea').post(resend_url(member_request.pk))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(mail.outbox, [])

    def test_member_cannot_resend_invite(self):
        member_request = self._approved_request(self.church_a)
        self._confirm(member_request)

        response = self._client(self.member_a, 'invitea').post(resend_url(member_request.pk))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(mail.outbox), 1)

    def test_admin_of_another_church_cannot_resend_invite(self):
        member_request = self._approved_request(self.church_a)
        self._confirm(member_request)

        response = self._client(self.admin_b, 'inviteb').post(resend_url(member_request.pk))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(mail.outbox), 1)
