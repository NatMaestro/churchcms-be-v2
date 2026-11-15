"""
Forgot-password must never return the reset token in the HTTP response.
It used to, which let anyone take over any account knowing only its email.
"""
import re
import secrets

from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.authentication.models import PasswordResetToken, User

FORGOT_URL = '/api/v1/auth/forgot-password/'
RESET_URL = '/api/v1/auth/reset-password/'
# Generated per run so no password literal lives in the repo.
ORIGINAL_PASSWORD = secrets.token_urlsafe(16)
NEW_PASSWORD = secrets.token_urlsafe(16)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    FRONTEND_URL='https://app.example.test',
)
class ForgotPasswordTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='victim@example.test', password=ORIGINAL_PASSWORD, name='Victim'
        )

    def _emailed_token(self):
        self.assertEqual(len(mail.outbox), 1)
        match = re.search(r'reset-password\?token=(\S+)', mail.outbox[-1].body)
        self.assertIsNotNone(match)
        return match.group(1)

    def test_response_never_contains_the_reset_token(self):
        response = self.client.post(FORGOT_URL, {'email': self.user.email}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('token', response.data)
        stored = PasswordResetToken.objects.get(user=self.user)
        self.assertNotIn(stored.token, response.content.decode())

    def test_reset_link_is_emailed_to_the_account_owner(self):
        self.client.post(FORGOT_URL, {'email': self.user.email}, format='json')

        self.assertEqual(mail.outbox[0].to, [self.user.email])
        token = self._emailed_token()
        self.assertTrue(PasswordResetToken.objects.filter(user=self.user, token=token).exists())

    def test_unknown_and_known_emails_get_identical_responses(self):
        known = self.client.post(FORGOT_URL, {'email': self.user.email}, format='json')
        unknown = self.client.post(FORGOT_URL, {'email': 'nobody@example.test'}, format='json')

        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.data, unknown.data)
        self.assertEqual(len(mail.outbox), 1)  # nothing sent for the unknown email

    def test_emailed_token_resets_password_and_only_newest_token_works(self):
        self.client.post(FORGOT_URL, {'email': self.user.email}, format='json')
        first_token = self._emailed_token()
        mail.outbox.clear()
        self.client.post(FORGOT_URL, {'email': self.user.email}, format='json')
        second_token = self._emailed_token()

        stale = self.client.post(
            RESET_URL, {'token': first_token, 'new_password': NEW_PASSWORD}, format='json'
        )
        fresh = self.client.post(
            RESET_URL, {'token': second_token, 'new_password': NEW_PASSWORD}, format='json'
        )

        self.assertEqual(stale.status_code, 400)
        self.assertEqual(fresh.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
