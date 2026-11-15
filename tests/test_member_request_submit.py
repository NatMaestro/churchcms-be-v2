"""
The public membership form posts here without a tenant header. MemberRequest
lives in each church's own schema, so the view must switch to the chosen
church's schema itself, and must not reveal who has already applied.
"""
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.test import TransactionTestCase
from django_tenants.utils import tenant_context
from rest_framework.test import APIClient

from apps.churches.models import Church
from apps.members.models import MemberRequest

SUBMIT_URL = '/api/v1/members/member-requests/submit/'
TEST_SCHEMAS = ('joina', 'joinb')
SUBMIT_RATE_LIMIT = 10


def application(**overrides):
    data = {
        'name': 'Ama Mensah',
        'email': 'ama@example.test',
        'phone': '0200000000',
        'address': '1 Test Street',
        'date_of_birth': '1990-05-17',
        'gender': 'female',
        'marital_status': 'single',
        'church_experience': 'Grew up in church',
        'reason_for_joining': 'Community',
        'how_did_you_hear': 'A friend',
        'emergency_contact': {'name': 'Kofi', 'phone': '0200000001', 'relationship': 'brother'},
        'skills': ['music'],
        'interests': ['choir'],
    }
    data.update(overrides)
    return data


class MemberRequestSubmitTests(TransactionTestCase):
    # See tests/test_tenant_binding.py: makes the flush use TRUNCATE ... CASCADE.
    available_apps = list(settings.INSTALLED_APPS)

    def setUp(self):
        cache.clear()  # throttle history lives in the cache
        connection.set_schema_to_public()
        self.church_a = self._make_church(TEST_SCHEMAS[0])
        self.church_b = self._make_church(TEST_SCHEMAS[1])
        self.client = APIClient()

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

    def _submit(self, subdomain='joina', **overrides):
        return self.client.post(
            SUBMIT_URL, {'subdomain': subdomain, **application(**overrides)}, format='json',
        )

    @staticmethod
    def _requests_in(church):
        with tenant_context(church):
            return list(MemberRequest.objects.values('email', 'status', 'church_id'))

    def test_application_is_stored_in_the_chosen_churchs_schema_only(self):
        response = self._submit('joina')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            self._requests_in(self.church_a),
            [{'email': 'ama@example.test', 'status': 'pending', 'church_id': self.church_a.pk}],
        )
        self.assertEqual(self._requests_in(self.church_b), [])

    def test_client_cannot_set_status_or_church(self):
        response = self._submit('joina', status='approved', church=self.church_b.pk)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            self._requests_in(self.church_a),
            [{'email': 'ama@example.test', 'status': 'pending', 'church_id': self.church_a.pk}],
        )
        self.assertEqual(self._requests_in(self.church_b), [])

    def test_response_does_not_expose_the_record_id(self):
        response = self._submit('joina')

        self.assertNotIn('data', response.json())

    def test_unknown_church_returns_404(self):
        response = self._submit('no-such-church')

        self.assertEqual(response.status_code, 404)

    def test_inactive_church_returns_404(self):
        Church.objects.filter(pk=self.church_a.pk).update(is_active=False)

        response = self._submit('joina')

        self.assertEqual(response.status_code, 404)

    def test_missing_subdomain_returns_400(self):
        response = self.client.post(SUBMIT_URL, application(), format='json')

        self.assertEqual(response.status_code, 400)

    def test_missing_required_field_returns_400(self):
        data = application()
        del data['date_of_birth']

        response = self.client.post(SUBMIT_URL, {'subdomain': 'joina', **data}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._requests_in(self.church_a), [])

    def test_repeat_application_looks_identical_and_creates_nothing(self):
        first = self._submit('joina')
        repeat = self._submit('joina', email='AMA@example.test')

        self.assertEqual(repeat.status_code, first.status_code)
        self.assertEqual(repeat.json(), first.json())
        self.assertEqual(len(self._requests_in(self.church_a)), 1)

    def test_same_email_can_apply_to_another_church(self):
        self._submit('joina')
        response = self._submit('joinb')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(self._requests_in(self.church_b)), 1)

    def test_submissions_are_rate_limited_per_client(self):
        for i in range(SUBMIT_RATE_LIMIT):
            self.assertEqual(self._submit('joina', email=f'person{i}@example.test').status_code, 201)

        response = self._submit('joina', email='one-too-many@example.test')

        self.assertEqual(response.status_code, 429)
        self.assertEqual(len(self._requests_in(self.church_a)), SUBMIT_RATE_LIMIT)
