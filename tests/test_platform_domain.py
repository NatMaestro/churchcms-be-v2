"""
The platform domain: churches live at <subdomain>.PLATFORM_DOMAIN, and while
visitors move over from an old domain, the old domain is still accepted.
"""
import re
from unittest import mock

from django.conf import settings
from django.core import mail
from django.db import connection
from django.test import RequestFactory, TestCase, override_settings

from apps.authentication.models import User
from apps.churches.models import Church, Domain
from apps.churches.provisioning import create_church_domains, send_church_admin_invite
from core.middleware.csrf import DynamicCSRFMiddleware

CHURCH_SITE = 'https://gracechapel.flocktend.com'
OLD_CHURCH_SITE = 'https://gracechapel.faithflow360.com'
LOOKALIKE_ORIGINS = (
    'https://gracechapel.flocktend.com.attacker.test',
    'https://evilflocktend.com',
    'http://gracechapel.flocktend.com',  # not HTTPS
    'https://gracechapel.example.test',
)


def csrf_trusts(origin):
    return DynamicCSRFMiddleware(lambda request: None)._origin_trusted(origin)


def cors_allows(origin):
    return any(re.match(pattern, origin) for pattern in settings.CORS_ALLOWED_ORIGIN_REGEXES)


class PlatformDomainTests(TestCase):
    def setUp(self):
        connection.set_schema_to_public()
        with mock.patch.object(Church, 'auto_create_schema', False):
            self.church = Church.objects.create(schema_name='gracechapel', subdomain='gracechapel',
                                                name='Grace Chapel', email='office@gracechapel.example.test')

    def test_the_default_platform_is_flocktend(self):
        self.assertEqual((settings.PLATFORM_NAME, settings.PLATFORM_DOMAIN), ('Flocktend', 'flocktend.com'))

    @override_settings(DEBUG=False)
    def test_a_new_church_gets_an_address_on_the_platform_domain(self):
        create_church_domains(self.church)

        self.assertTrue(Domain.objects.filter(tenant=self.church, domain='gracechapel.flocktend.com').exists())
        self.assertFalse(Domain.objects.filter(domain__endswith='faithflow360.com').exists())

    @override_settings(DEBUG=False, PLATFORM_DOMAIN='churches.example.test')
    def test_the_church_address_follows_the_platform_domain_setting(self):
        create_church_domains(self.church)

        self.assertTrue(Domain.objects.filter(domain='gracechapel.churches.example.test').exists())

    def test_church_sites_on_the_new_and_old_domain_are_trusted(self):
        for origin in (CHURCH_SITE, OLD_CHURCH_SITE, 'https://www.flocktend.com', 'https://my-church.flocktend.com'):
            self.assertTrue(csrf_trusts(origin), origin)
            self.assertTrue(cors_allows(origin), origin)

    def test_lookalike_and_unknown_origins_are_not_trusted(self):
        for origin in LOOKALIKE_ORIGINS:
            self.assertFalse(csrf_trusts(origin), origin)
            self.assertFalse(cors_allows(origin), origin)

    @override_settings(ACCEPTED_PLATFORM_DOMAINS=['flocktend.com'])
    def test_the_old_domain_stops_being_trusted_once_it_is_dropped(self):
        self.assertFalse(csrf_trusts(OLD_CHURCH_SITE))
        self.assertTrue(csrf_trusts(CHURCH_SITE))

    def test_the_security_policy_allows_the_platform_api(self):
        from core.middleware.security import SecurityHeadersMiddleware
        from django.http import HttpResponse

        with override_settings(DEBUG=False):
            response = SecurityHeadersMiddleware(lambda request: HttpResponse())(RequestFactory().get('/'))

        self.assertIn('https://api.flocktend.com', response['Content-Security-Policy'])

    @override_settings(FRONTEND_URL='https://www.flocktend.com')
    def test_the_admin_invite_email_uses_the_new_name_and_address(self):
        admin = User.objects.create_user(email='ama@gracechapel.example.test', password=None, name='Ama',
                                         church=self.church, role='admin')

        send_church_admin_invite(admin, self.church)

        email = mail.outbox[0]
        self.assertEqual(email.subject, 'Grace Chapel is ready on Flocktend')
        self.assertIn('set up on Flocktend', email.body)
        self.assertIn(f'{CHURCH_SITE}/reset-password?token=', email.body)
        self.assertNotIn('FaithFlow', email.body)
