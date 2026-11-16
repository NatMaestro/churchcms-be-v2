"""
Email links open on the person's own church site (<subdomain>.<main domain>),
for any church, and on the main site for people without a church.
"""
from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings

from core.frontend_links import frontend_url

PATH = '/reset-password?token=abc'


def church(subdomain):
    return SimpleNamespace(subdomain=subdomain)


class FrontendUrlTests(SimpleTestCase):
    @override_settings(FRONTEND_URL='https://www.faithflow360.com')
    def test_church_link_replaces_www_with_the_church_subdomain(self):
        self.assertEqual(frontend_url(PATH, church('olamchurch')),
                         'https://olamchurch.faithflow360.com/reset-password?token=abc')

    @override_settings(FRONTEND_URL='https://www.faithflow360.com')
    def test_every_church_gets_its_own_subdomain(self):
        self.assertEqual(frontend_url(PATH, church('gracechapel')),
                         'https://gracechapel.faithflow360.com/reset-password?token=abc')

    @override_settings(FRONTEND_URL='https://faithflow360.com/')
    def test_main_domain_without_www_or_with_trailing_slash(self):
        self.assertEqual(frontend_url(PATH, church('olamchurch')),
                         'https://olamchurch.faithflow360.com/reset-password?token=abc')

    @override_settings(FRONTEND_URL='http://localhost:8080')
    def test_local_development_keeps_scheme_and_port(self):
        self.assertEqual(frontend_url(PATH, church('demochurch')),
                         'http://demochurch.localhost:8080/reset-password?token=abc')

    @override_settings(FRONTEND_URL='https://www.faithflow360.com')
    def test_no_church_uses_the_main_site(self):
        self.assertEqual(frontend_url(PATH), 'https://www.faithflow360.com/reset-password?token=abc')
        self.assertEqual(frontend_url(PATH, church('')),
                         'https://www.faithflow360.com/reset-password?token=abc')
