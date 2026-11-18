"""
api/v1/setup/initial/ created a church and admin with no sign-in, guarded only by
a token that fell back to SECRET_KEY[:32]. It sat in config/urls_public.py, which
is only served if TenantMainMiddleware is switched back on. Churches are created
by sign-up or by a platform admin, so the endpoint is gone from every URL config.
"""
from django.test import SimpleTestCase
from django.urls import Resolver404, resolve

SETUP_PATH = '/api/v1/setup/initial/'


class InitialSetupEndpointRemovedTests(SimpleTestCase):
    def test_no_url_config_serves_the_old_setup_endpoint(self):
        for urlconf in ('config.urls_tenants', 'config.urls_public'):
            with self.subTest(urlconf=urlconf), self.assertRaises(Resolver404):
                resolve(SETUP_PATH, urlconf=urlconf)
