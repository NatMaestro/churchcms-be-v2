"""
A module a church has switched off is refused by the API, not just hidden from
the menu. Churches with no module setting saved (created before modules
existed) keep every module on.
"""
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.test import SimpleTestCase, TransactionTestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import User
from apps.churches.models import Church
from apps.churches.module_access import module_is_on, requires_module
from apps.churches.setup_rules import MODULE_KEYS

SCHEMA = 'modulechurch'

# One list endpoint per module, as the admin dashboard calls them.
MODULE_URLS = {
    'giving': ['/api/v1/payments/', '/api/v1/payments/pledges/'],
    'dues': ['/api/v1/dues/plans/', '/api/v1/dues/payments/', '/api/v1/dues/my-card/'],
    'events': ['/api/v1/events/'],
    'prayerRequests': ['/api/v1/prayer-requests/'],
    'volunteers': ['/api/v1/volunteer-opportunities/', '/api/v1/volunteer-signups/', '/api/v1/volunteer-hours/'],
    'ministries': ['/api/v1/ministries/'],
    'serviceRequests': ['/api/v1/service-requests/'],
    'altarCalls': ['/api/v1/altar-calls/'],
}

# Actions any signed-in member may use, which have their own permission rules.
MEMBER_ACTIONS = {
    'events': '/api/v1/events/999999/register/',
    'ministries': '/api/v1/ministries/999999/join/',
    'volunteers': '/api/v1/volunteer-opportunities/999999/signup/',
}


class ModuleIsOnTests(SimpleTestCase):
    def test_a_module_is_on_unless_switched_off(self):
        cases = [
            ({}, True),
            ({'modules': None}, True),
            ({'modules': {}}, True),
            ({'modules': {'dues': True}}, True),
            ({'modules': {'giving': False}}, True),
            ({'modules': {'dues': False}}, False),
        ]
        for features, expected in cases:
            with self.subTest(features=features):
                self.assertEqual(module_is_on(Church(features=features), 'dues'), expected)

    def test_a_church_with_no_features_has_every_module_on(self):
        self.assertTrue(module_is_on(Church(features=None), 'dues'))

    def test_an_unknown_module_name_is_a_programming_error(self):
        with self.assertRaises(ValueError):
            requires_module('nosuchmodule')

    def test_every_module_has_endpoints_covered_here(self):
        self.assertEqual(set(MODULE_URLS), set(MODULE_KEYS))


class ModuleAccessTests(TransactionTestCase):
    # See tests/test_tenant_binding.py: makes the flush use TRUNCATE ... CASCADE.
    available_apps = list(settings.INSTALLED_APPS)

    def setUp(self):
        cache.clear()
        connection.set_schema_to_public()
        self.church = Church.objects.create(schema_name=SCHEMA, subdomain=SCHEMA, name='Module Church',
                                            email='office@module.example.test', bypass_subscription_check=True)
        self.admin = User.objects.create_user(email='admin@module.example.test', password='pass-12345',
                                              name='Pastor', church=self.church, role='admin')
        self.member = User.objects.create_user(email='ama@module.example.test', password='pass-12345',
                                               name='Ama', church=self.church, role='member')

    def tearDown(self):
        cache.clear()
        connection.set_schema_to_public()
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE')

    @staticmethod
    def _client(user):
        client = APIClient()
        token = RefreshToken.for_user(user).access_token
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}', HTTP_X_TENANT_SUBDOMAIN=SCHEMA)
        return client

    def _set_modules(self, modules):
        connection.set_schema_to_public()
        self.church.features = {'modules': modules}
        self.church.save(update_fields=['features'])

    def test_a_switched_off_module_is_refused(self):
        self._set_modules({key: False for key in MODULE_KEYS})
        admin = self._client(self.admin)

        for key, urls in MODULE_URLS.items():
            for url in urls:
                with self.subTest(module=key, url=url):
                    response = admin.get(url)
                    self.assertEqual(response.status_code, 403)
                    self.assertIn("isn't switched on for this church", str(response.data['error']))

    def test_member_actions_of_a_switched_off_module_are_refused(self):
        self._set_modules({key: False for key in MODULE_KEYS})
        member = self._client(self.member)

        for key, url in MEMBER_ACTIONS.items():
            with self.subTest(module=key):
                self.assertEqual(member.post(url).status_code, 403)

    def test_a_switched_on_module_is_allowed(self):
        self._set_modules({key: True for key in MODULE_KEYS})
        admin = self._client(self.admin)

        for key, urls in MODULE_URLS.items():
            for url in urls:
                if url.endswith('my-card/'):
                    continue  # an admin has no member card; covered by the refusal test
                with self.subTest(module=key, url=url):
                    self.assertEqual(admin.get(url).status_code, 200)

    def test_member_actions_of_a_switched_on_module_reach_the_view(self):
        self._set_modules({key: True for key in MODULE_KEYS})
        member = self._client(self.member)

        for key, url in MEMBER_ACTIONS.items():
            with self.subTest(module=key):
                self.assertEqual(member.post(url).status_code, 404)  # no such record, but not refused

    def test_a_church_with_no_module_setting_keeps_every_module(self):
        connection.set_schema_to_public()
        self.church.features = {}
        self.church.save(update_fields=['features'])
        admin = self._client(self.admin)

        for key, urls in MODULE_URLS.items():
            with self.subTest(module=key):
                self.assertEqual(admin.get(urls[0]).status_code, 200)

    def test_switching_one_module_off_leaves_the_others_alone(self):
        self._set_modules({'dues': False})
        admin = self._client(self.admin)

        self.assertEqual(admin.get('/api/v1/dues/plans/').status_code, 403)
        self.assertEqual(admin.get('/api/v1/events/').status_code, 200)
        self.assertEqual(admin.get('/api/v1/payments/').status_code, 200)

    def test_switching_a_module_back_on_takes_effect_at_once(self):
        admin = self._client(self.admin)
        self._set_modules({'events': False})
        self.assertEqual(admin.get('/api/v1/events/').status_code, 403)

        self._set_modules({'events': True})
        self.assertEqual(admin.get('/api/v1/events/').status_code, 200)
