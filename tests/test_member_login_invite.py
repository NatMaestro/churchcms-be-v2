"""
An admin gives a member added by hand their login: the login is created with
no usable password, linked to the member, and the member is emailed a
single-use link to set their own password. No password is ever chosen for
them. Runs against real tenant schemas and Django's in-memory mailbox.
"""
from smtplib import SMTPException
from unittest import mock

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.db import connection
from django.test import TransactionTestCase, override_settings
from django_tenants.utils import tenant_context
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import User
from apps.churches.models import Church
from apps.members.models import Member

TEST_SCHEMAS = ('logininvitea', 'logininviteb')
SEND_MAIL = 'apps.members.member_request_notifications.send_mail'
MEMBER_EMAIL = 'ama@logininvite.example.test'
NEW_PASSWORD = 'chosen-by-member-123'
RESET_URL = '/api/v1/auth/reset-password/'


def invite_url(member_id):
    return f'/api/v1/members/{member_id}/invite/'


@override_settings(FRONTEND_URL='https://www.flocktend.example.test')
class MemberLoginInviteTests(TransactionTestCase):
    # See tests/test_tenant_binding.py: makes the flush use TRUNCATE ... CASCADE.
    available_apps = list(settings.INSTALLED_APPS)

    def setUp(self):
        cache.clear()
        connection.set_schema_to_public()
        self.church_a = self._make_church(TEST_SCHEMAS[0])
        self.church_b = self._make_church(TEST_SCHEMAS[1])
        self.admin_a = self._make_user('admin@login-a.test', self.church_a, 'admin')
        self.admin_b = self._make_user('admin@login-b.test', self.church_b, 'admin')
        self.plain_member = self._make_user('member@login-a.test', self.church_a, 'member')
        with tenant_context(self.church_a):
            self.member = Member.objects.create(member_id='L-1', first_name='Ama', last_name='Mensah',
                                                email=MEMBER_EMAIL)
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
    def _client(user, subdomain=TEST_SCHEMAS[0]):
        client = APIClient()
        token = RefreshToken.for_user(user).access_token
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}', HTTP_X_TENANT_SUBDOMAIN=subdomain)
        return client

    def _invite(self, user=None, subdomain=TEST_SCHEMAS[0], member_id=None):
        client = self._client(user or self.admin_a, subdomain)
        return client.post(invite_url(member_id or self.member.pk), format='json')

    def _reload_member(self):
        with tenant_context(self.church_a):
            return Member.objects.select_related('user').get(pk=self.member.pk)

    def test_invite_creates_a_linked_login_with_no_password_and_emails_a_link(self):
        response = self._invite()

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['data']['invite_sent'])
        user = User.objects.get(email=MEMBER_EMAIL)
        self.assertFalse(user.has_usable_password())
        self.assertEqual((user.role, user.church_id, user.name), ('member', self.church_a.pk, 'Ama Mensah'))
        self.assertTrue(user.must_change_password)
        self.assertEqual(self._reload_member().user_id, user.pk)
        self.assertEqual([m.to for m in mail.outbox], [[MEMBER_EMAIL]])
        self.assertIn('has added you as a member', mail.outbox[0].body)
        self.assertIn('/reset-password?token=', mail.outbox[0].body)

    def test_response_never_contains_a_password(self):
        response = self._invite()

        self.assertEqual(set(response.json()['data']), {'user_id', 'login_email', 'invite_sent'})

    def test_member_can_set_a_password_from_the_link_and_the_link_works_once(self):
        self._invite()
        token = mail.outbox[0].body.split('token=')[1].split('&')[0]

        first = APIClient().post(RESET_URL, {'token': token, 'new_password': NEW_PASSWORD}, format='json')
        again = APIClient().post(RESET_URL, {'token': token, 'new_password': NEW_PASSWORD}, format='json')

        self.assertEqual(first.status_code, 200)
        self.assertEqual(again.status_code, 400)
        self.assertTrue(User.objects.get(email=MEMBER_EMAIL).check_password(NEW_PASSWORD))

    def test_inviting_again_sends_a_fresh_link_without_a_second_login(self):
        self._invite()
        response = self._invite()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email=MEMBER_EMAIL).count(), 1)
        self.assertEqual(len(mail.outbox), 2)

    def test_a_member_who_has_set_a_password_is_not_sent_another_invite(self):
        self._invite()
        user = User.objects.get(email=MEMBER_EMAIL)
        user.set_password(NEW_PASSWORD)
        user.save()
        mail.outbox = []

        response = self._invite()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(mail.outbox, [])

    def test_an_email_that_already_has_a_login_is_refused(self):
        with tenant_context(self.church_a):
            Member.objects.filter(pk=self.member.pk).update(email='admin@login-b.test')

        response = self._invite()

        self.assertEqual(response.status_code, 409)
        self.assertIsNone(self._reload_member().user_id)
        self.assertEqual(mail.outbox, [])

    def test_a_member_without_an_email_is_refused(self):
        with tenant_context(self.church_a):
            Member.objects.filter(pk=self.member.pk).update(email='')

        response = self._invite()

        self.assertEqual(response.status_code, 400)
        self.assertIsNone(self._reload_member().user_id)

    def test_a_member_cannot_invite(self):
        response = self._invite(user=self.plain_member)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(email=MEMBER_EMAIL).exists())

    def test_another_churchs_admin_cannot_invite_this_churchs_member(self):
        response = self._invite(user=self.admin_b, subdomain=TEST_SCHEMAS[1])

        self.assertEqual(response.status_code, 404)
        self.assertFalse(User.objects.filter(email=MEMBER_EMAIL).exists())
        self.assertEqual(mail.outbox, [])

    def test_login_is_kept_when_the_first_email_fails(self):
        with mock.patch(SEND_MAIL, side_effect=SMTPException('down')):
            response = self._invite()

        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()['data']['invite_sent'])
        self.assertIsNotNone(self._reload_member().user_id)

    def test_a_failed_resend_is_reported(self):
        self._invite()
        with mock.patch(SEND_MAIL, side_effect=SMTPException('down')):
            response = self._invite()

        self.assertEqual(response.status_code, 502)
