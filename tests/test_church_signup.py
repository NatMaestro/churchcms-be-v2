"""
Church sign-up: the web address follows one set of rules (sign-up and the
live check agree), an email belongs to one account, the church's chosen
modules are stored, and only the church admin can change them later.
"""
from django.conf import settings
from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import User
from apps.churches.models import Church

REGISTER = '/api/v1/auth/register/'
CHECK = '/api/v1/churches/validate_subdomain/'
PASSWORD = 'StrongPass-2026'


def signup(**overrides):
    body = {
        'church_name': "St. Mary's Parish", 'subdomain': 'stmarys', 'name': 'Father Kwame',
        'email': 'kwame@stmarys.example.test', 'password': PASSWORD, 'password_confirm': PASSWORD,
        'denomination': 'Catholic', 'phone': '0302123456',
        'features': {'modules': {'giving': True, 'dues': True, 'altarCalls': False}},
    }
    body.update(overrides)
    return APIClient().post(REGISTER, body, format='json')


class ChurchSignupTests(TestCase):
    def setUp(self):
        connection.set_schema_to_public()

    def tearDown(self):
        connection.set_schema_to_public()
        super().tearDown()

    def test_a_church_signs_up_with_its_address_phone_and_modules(self):
        response = signup()

        self.assertEqual(response.status_code, 201, response.content)
        church = Church.objects.get(subdomain='stmarys')
        self.assertEqual((church.name, church.phone, church.plan), ("St. Mary's Parish", '0302123456', 'trial'))
        self.assertEqual(church.features['modules'], {'giving': True, 'dues': True, 'altarCalls': False})
        # Signed in straight away: the response sets the auth cookies.
        self.assertIn(settings.ACCESS_TOKEN_COOKIE_NAME, response.cookies)

    def test_addresses_that_are_not_valid_hostnames_are_refused(self):
        for bad in ("st.mary's", 'st_marys', 'st marys', '-stmarys', 'ab', 'a' * 41):
            response = signup(subdomain=bad)
            self.assertEqual(response.status_code, 400, bad)
            self.assertIn('subdomain', response.data['errors'], bad)
        self.assertFalse(Church.objects.exclude(schema_name='public').exists())

    def test_reserved_addresses_are_refused(self):
        for reserved in ('api', 'www', 'admin', 'flocktend'):
            response = signup(subdomain=reserved)
            self.assertEqual(response.status_code, 400, reserved)
            self.assertIn('reserved', str(response.data['errors']['subdomain'][0]), reserved)

    def test_an_address_is_normalized_to_lowercase(self):
        self.assertEqual(signup(subdomain='  StMarys ').status_code, 201)
        self.assertTrue(Church.objects.filter(subdomain='stmarys').exists())

    def test_a_taken_address_is_refused(self):
        signup()

        response = signup(email='other@stmarys.example.test')

        self.assertEqual(response.status_code, 400)
        self.assertIn('already taken', str(response.data['errors']['subdomain'][0]))

    def test_an_email_that_already_has_an_account_is_refused_before_anything_is_created(self):
        User.objects.create_user(email='kwame@stmarys.example.test', password=PASSWORD, name='Kwame')

        response = signup(email='KWAME@stmarys.example.test')

        self.assertEqual(response.status_code, 400)
        self.assertIn('Sign in instead', str(response.data['errors']['email'][0]))
        self.assertFalse(Church.objects.filter(subdomain='stmarys').exists())

    def test_unknown_modules_are_refused(self):
        response = signup(features={'modules': {'giving': True, 'teleportation': True}})

        self.assertEqual(response.status_code, 400)
        self.assertIn('teleportation', str(response.data['errors']['features'][0]))

    def test_mismatched_passwords_are_reported_on_the_confirmation(self):
        response = signup(password_confirm='Different-2026')

        self.assertEqual(response.status_code, 400)
        self.assertIn('password_confirm', response.data['errors'])

    # --- the live address check uses the same rules ---

    def test_the_live_check_agrees_with_sign_up(self):
        signup()
        client = APIClient()

        def check(value):
            return client.post(CHECK, {'subdomain': value}, format='json').data

        self.assertEqual((check('newparish')['available'], check('newparish')['message']), (True, ''))
        self.assertFalse(check('stmarys')['available'])
        self.assertIn('already taken', check('stmarys')['message'])
        self.assertFalse(check('api')['available'])
        self.assertIn('reserved', check('api')['message'])
        self.assertFalse(check('st_marys')['available'])

    # --- changing modules later ---

    def test_the_church_admin_changes_modules_and_members_cannot(self):
        signup()
        church = Church.objects.get(subdomain='stmarys')
        admin = User.objects.get(email='kwame@stmarys.example.test')
        member = User.objects.create_user(email='ama@stmarys.example.test', password=PASSWORD, name='Ama',
                                          church=church, role='member')

        def client_for(user):
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}',
                               HTTP_X_TENANT_SUBDOMAIN='stmarys')
            return client

        url = f'/api/v1/churches/{church.pk}/features/'
        body = {'features': {'modules': {'giving': True, 'dues': False, 'altarCalls': True}}}
        self.assertEqual(client_for(member).put(url, body, format='json').status_code, 403)
        self.assertEqual(client_for(admin).put(url, {'features': {'modules': {'nope': True}}},
                                               format='json').status_code, 400)

        response = client_for(admin).put(url, body, format='json')

        self.assertEqual(response.status_code, 200, response.content)
        church.refresh_from_db()
        self.assertEqual(church.features['modules'], {'giving': True, 'dues': False, 'altarCalls': True})

