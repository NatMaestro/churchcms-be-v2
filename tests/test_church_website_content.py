"""
A church's own website reads its public content from FaithFlow without
logging in. Only events and announcements the admin marked "show on website"
appear, only that church's content is returned, and nothing identifying a
member ever leaves the system.
"""
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from django_tenants.utils import tenant_context
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.announcements.models import Announcement
from apps.authentication.models import User
from apps.churches.models import Church
from apps.churches.views_public_website import MAX_EVENTS, WEBSITE_CONTENT_VERSION
from apps.events.models import Event
from apps.ministries.models import Ministry

TEST_SCHEMAS = ('sitea', 'siteb')
ADMIN_EMAIL = 'admin@site-a.example.test'
ATTENDEE_ID = 987654
EVENT_FIELDS = {'id', 'title', 'description', 'start', 'end', 'location', 'type',
                'is_recurring', 'recurrence_pattern'}
ANNOUNCEMENT_FIELDS = {'id', 'title', 'content', 'type', 'is_urgent', 'starts_at', 'expires_at'}
MINISTRY_FIELDS = {'id', 'name', 'description', 'category', 'meeting_schedule', 'location'}


def content_url(subdomain):
    return f'/api/v1/churches/{subdomain}/website/'


class ChurchWebsiteContentTests(TransactionTestCase):
    # See tests/test_tenant_binding.py: makes the flush use TRUNCATE ... CASCADE.
    available_apps = list(settings.INSTALLED_APPS)

    def setUp(self):
        cache.clear()  # throttle history lives in the cache
        connection.set_schema_to_public()
        self.church_a = self._make_church(TEST_SCHEMAS[0])
        self.church_b = self._make_church(TEST_SCHEMAS[1])
        self.admin_a = User.objects.create_user(
            email=ADMIN_EMAIL, password='pass-12345', name='Site Admin',
            church=self.church_a, role='admin',
        )
        self.now = timezone.now()

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

    def _event(self, church, title, **fields):
        values = {
            'description': f'{title} description', 'location': 'Main Church',
            'date': self.now + timedelta(days=3), 'show_on_website': True,
            'attendees': [ATTENDEE_ID], 'created_by': self.admin_a,
        }
        values.update(fields)
        with tenant_context(church):
            return Event.objects.create(title=title, **values)

    def _announcement(self, church, title, **fields):
        values = {'content': f'{title} text', 'show_on_website': True, 'created_by': self.admin_a}
        values.update(fields)
        with tenant_context(church):
            return Announcement.objects.create(title=title, **values)

    def _ministry(self, church, name, **fields):
        values = {'description': f'{name} description', 'category': 'worship',
                  'meeting_schedule': 'Saturdays 4pm', 'created_by': self.admin_a}
        values.update(fields)
        with tenant_context(church):
            return Ministry.objects.create(name=name, **values)

    def _get(self, subdomain=TEST_SCHEMAS[0]):
        response = APIClient().get(content_url(subdomain))
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    @staticmethod
    def _titles(items, key='title'):
        return [item[key] for item in items]

    # --- what appears ---

    def test_no_login_needed_and_response_is_versioned(self):
        body = self._get()

        self.assertEqual(body['version'], WEBSITE_CONTENT_VERSION)
        self.assertEqual(body['events'], [])
        self.assertEqual(body['announcements'], [])
        self.assertEqual(body['ministries'], [])

    def test_only_events_marked_for_the_website_appear(self):
        self._event(self.church_a, 'Harvest Mass')
        self._event(self.church_a, 'Finance committee', show_on_website=False)

        self.assertEqual(self._titles(self._get()['events']), ['Harvest Mass'])

    def test_past_one_off_events_are_hidden(self):
        self._event(self.church_a, 'Last week', date=self.now - timedelta(days=7))
        self._event(self.church_a, 'Next week', date=self.now + timedelta(days=7))

        self.assertEqual(self._titles(self._get()['events']), ['Next week'])

    def test_recurring_series_shows_until_it_ends(self):
        started = self.now - timedelta(days=30)
        self._event(self.church_a, 'Sunday Mass', date=started, is_recurring=True,
                    recurrence_pattern='weekly')
        self._event(self.church_a, 'Lent talks', date=started, is_recurring=True,
                    recurrence_pattern='weekly',
                    recurrence_end_date=(self.now - timedelta(days=1)).date())

        self.assertEqual(self._titles(self._get()['events']), ['Sunday Mass'])

    def test_events_are_soonest_first_and_capped(self):
        for day in range(MAX_EVENTS + 5, 0, -1):
            self._event(self.church_a, f'Event {day:03d}', date=self.now + timedelta(days=day))

        events = self._get()['events']

        self.assertEqual(len(events), MAX_EVENTS)
        self.assertEqual(events[0]['title'], 'Event 001')

    def test_only_current_announcements_marked_for_the_website_appear(self):
        self._announcement(self.church_a, 'Parish picnic')
        self._announcement(self.church_a, 'Not for website', show_on_website=False)
        self._announcement(self.church_a, 'Switched off', is_active=False)
        self._announcement(self.church_a, 'Expired', expires_at=self.now - timedelta(hours=1))
        self._announcement(self.church_a, 'Not yet', scheduled_at=self.now + timedelta(days=1))

        self.assertEqual(self._titles(self._get()['announcements']), ['Parish picnic'])

    def test_only_active_ministries_appear(self):
        self._ministry(self.church_a, 'Choir')
        self._ministry(self.church_a, 'Disbanded group', is_active=False)

        self.assertEqual(self._titles(self._get()['ministries'], key='name'), ['Choir'])

    # --- what never appears ---

    def test_response_contains_no_member_details(self):
        self._event(self.church_a, 'Harvest Mass')
        self._announcement(self.church_a, 'Parish picnic')
        self._ministry(self.church_a, 'Choir')

        response = APIClient().get(content_url(TEST_SCHEMAS[0]))
        body = response.json()

        self.assertEqual(set(body['events'][0]), EVENT_FIELDS)
        self.assertEqual(set(body['announcements'][0]), ANNOUNCEMENT_FIELDS)
        self.assertEqual(set(body['ministries'][0]), MINISTRY_FIELDS)
        text = response.content.decode()
        self.assertNotIn(ADMIN_EMAIL, text)
        self.assertNotIn('Site Admin', text)
        self.assertNotIn(str(ATTENDEE_ID), text)

    def test_another_churchs_content_is_never_returned(self):
        self._event(self.church_b, 'Other church event')
        self._announcement(self.church_b, 'Other church news')
        self._ministry(self.church_b, 'Other church choir')

        body = self._get(TEST_SCHEMAS[0])

        self.assertEqual(body['events'], [])
        self.assertEqual(body['announcements'], [])
        self.assertEqual(body['ministries'], [])

    def test_unknown_or_inactive_church_returns_404(self):
        self.church_b.is_active = False
        self.church_b.save(update_fields=['is_active'])

        self.assertEqual(APIClient().get(content_url('nosuchchurch')).status_code, 404)
        self.assertEqual(APIClient().get(content_url(TEST_SCHEMAS[1])).status_code, 404)

    def test_query_count_does_not_grow_with_content(self):
        self._event(self.church_a, 'One')
        self._announcement(self.church_a, 'One')
        self._ministry(self.church_a, 'One')
        with CaptureQueriesContext(connection) as few:
            self._get()

        for n in range(5):
            self._event(self.church_a, f'More {n}')
            self._announcement(self.church_a, f'More {n}')
            self._ministry(self.church_a, f'More {n}')
        with CaptureQueriesContext(connection) as many:
            self._get()

        self.assertEqual(len(many), len(few))

    # --- admin side ---

    def test_admin_can_mark_an_event_for_the_website(self):
        event = self._event(self.church_a, 'Harvest Mass', show_on_website=False)
        client = APIClient()
        token = RefreshToken.for_user(self.admin_a).access_token
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}',
                           HTTP_X_TENANT_SUBDOMAIN=TEST_SCHEMAS[0])

        response = client.patch(f'/api/v1/events/{event.pk}/', {'show_on_website': True},
                                format='json')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self._titles(self._get()['events']), ['Harvest Mass'])
