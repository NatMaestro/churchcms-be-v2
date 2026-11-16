"""
The token blacklist app was not installed, so logout raised, returned 400 and
left the auth cookies in place, and refresh tokens could never be revoked.
"""
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from apps.authentication.models import User

LOGIN_URL = '/api/v1/auth/login/'
LOGOUT_URL = '/api/v1/auth/logout/'
REFRESH_URL = '/api/v1/auth/refresh/'


class LogoutRevocationTests(TestCase):
    def setUp(self):
        User.objects.create_user(email='person@example.test', password='pass-12345', name='Person')
        self.client = APIClient()
        login = self.client.post(
            LOGIN_URL, {'email': 'person@example.test', 'password': 'pass-12345'}, format='json'
        )
        self.assertEqual(login.status_code, 200)
        self.refresh = login.data['refresh']

    def test_logout_succeeds_and_clears_auth_cookies(self):
        response = self.client.post(LOGOUT_URL, {}, format='json')

        self.assertEqual(response.status_code, 200)
        for name in (settings.ACCESS_TOKEN_COOKIE_NAME, settings.REFRESH_TOKEN_COOKIE_NAME):
            self.assertEqual(response.cookies[name].value, '')

    def test_refresh_token_is_unusable_after_logout(self):
        self.client.post(LOGOUT_URL, {}, format='json')

        response = APIClient().post(REFRESH_URL, {'refresh': self.refresh}, format='json')

        self.assertEqual(response.status_code, 401)

    def test_rotated_refresh_token_cannot_be_reused(self):
        first = APIClient().post(REFRESH_URL, {'refresh': self.refresh}, format='json')
        replay = APIClient().post(REFRESH_URL, {'refresh': self.refresh}, format='json')

        self.assertEqual(first.status_code, 200)
        self.assertEqual(replay.status_code, 401)
