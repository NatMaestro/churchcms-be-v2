"""
Volunteering: a member signs up for and withdraws from opportunities as
themselves and sees only their own sign-ups; church staff create
opportunities and approve or decline sign-ups. Spot counts stay accurate.
"""
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.test import TransactionTestCase
from django_tenants.utils import tenant_context
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import User
from apps.churches.models import Church
from apps.members.models import Member
from apps.volunteers.models import VolunteerHours, VolunteerOpportunity, VolunteerSignup

SCHEMA = 'volunteerchurch'
OPPS = '/api/v1/volunteer-opportunities/'
SIGNUPS = '/api/v1/volunteer-signups/'
HOURS = '/api/v1/volunteer-hours/'


def results(response):
    data = response.data
    return data['results'] if isinstance(data, dict) and 'results' in data else data


class VolunteerTests(TransactionTestCase):
    # See tests/test_tenant_binding.py: makes the flush use TRUNCATE ... CASCADE.
    available_apps = list(settings.INSTALLED_APPS)

    def setUp(self):
        cache.clear()
        connection.set_schema_to_public()
        self.church = Church.objects.create(schema_name=SCHEMA, subdomain=SCHEMA, name='Volunteer Church',
                                            email='office@volunteer.example.test', bypass_subscription_check=True)
        self.admin = self._user('admin@volunteer.example.test', 'admin')
        self.kofi_user = self._user('kofi@volunteer.example.test', 'member')
        self.esi_user = self._user('esi@volunteer.example.test', 'member')
        self.unlinked_user = self._user('new@volunteer.example.test', 'member')
        with tenant_context(self.church):
            self.kofi = Member.objects.create(user=self.kofi_user, member_id='V-1', first_name='Kofi',
                                              last_name='Mensah', email='kofi@volunteer.example.test',
                                              phone='0201111111')
            self.esi = Member.objects.create(user=self.esi_user, member_id='V-2', first_name='Esi',
                                             last_name='Owusu', email='esi@volunteer.example.test')
            self.ushers = VolunteerOpportunity.objects.create(
                title='Ushers', description='Welcome people on Sunday.', category='ministry',
                location='Main hall', spots_available=2)
            self.archived = VolunteerOpportunity.objects.create(
                title='Old project', description='Finished.', category='other', location='Hall', is_active=False)

    def tearDown(self):
        cache.clear()
        connection.set_schema_to_public()
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE')

    def _user(self, email, role):
        return User.objects.create_user(email=email, password='pass-12345', name=email.split('@')[0],
                                        church=self.church, role=role)

    @staticmethod
    def _client(user):
        client = APIClient()
        token = RefreshToken.for_user(user).access_token
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}', HTTP_X_TENANT_SUBDOMAIN=SCHEMA)
        return client

    def _signup(self, user, **data):
        return self._client(user).post(f'{OPPS}{self.ushers.pk}/signup/', data, format='json')

    def _row(self, user, opportunity_id=None):
        rows = results(self._client(user).get(OPPS))
        return next(row for row in rows if row['id'] == (opportunity_id or self.ushers.pk))

    def _signups(self):
        with tenant_context(self.church):
            return {(s.member_id, s.status) for s in VolunteerSignup.objects.all()}

    # --- opportunities ---

    def test_members_see_active_opportunities_and_staff_see_all(self):
        member_titles = {row['title'] for row in results(self._client(self.kofi_user).get(OPPS))}
        staff_titles = {row['title'] for row in results(self._client(self.admin).get(OPPS))}

        self.assertEqual(member_titles, {'Ushers'})
        self.assertEqual(staff_titles, {'Ushers', 'Old project'})

    def test_staff_create_opportunities_and_members_cannot(self):
        data = {'title': 'Choir', 'description': 'Sing.', 'category': 'ministry', 'location': 'Hall'}

        self.assertEqual(self._client(self.admin).post(OPPS, data, format='json').status_code, 201)
        self.assertEqual(self._client(self.kofi_user).post(OPPS, data, format='json').status_code, 403)

    # --- signing up ---

    def test_a_member_signs_up_as_themselves(self):
        response = self._signup(self.kofi_user, member_id=self.esi.pk, notes='Free on Sundays')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self._signups(), {(self.kofi.pk, 'pending')})
        row = self._row(self.kofi_user)
        self.assertEqual((row['my_signup_status'], row['spots_filled'], row['spots_left']), ('pending', 1, 1))
        self.assertIsNone(self._row(self.esi_user)['my_signup_status'])

    def test_signing_up_twice_is_refused(self):
        self._signup(self.kofi_user)

        self.assertEqual(self._signup(self.kofi_user).status_code, 400)
        self.assertEqual(self._row(self.admin)['spots_filled'], 1)

    def test_a_full_opportunity_refuses_more_volunteers(self):
        with tenant_context(self.church):
            VolunteerOpportunity.objects.filter(pk=self.ushers.pk).update(spots_available=1)
        self._signup(self.esi_user)

        self.assertEqual(self._signup(self.kofi_user).status_code, 400)

    def test_a_login_without_a_member_record_cannot_sign_up(self):
        self.assertEqual(self._signup(self.unlinked_user).status_code, 400)

    def test_withdrawing_frees_the_spot_and_signing_up_again_works(self):
        client = self._client(self.kofi_user)
        self._signup(self.kofi_user)

        self.assertEqual(client.post(f'{OPPS}{self.ushers.pk}/withdraw/').status_code, 200)
        self.assertEqual(self._row(self.kofi_user)['spots_filled'], 0)
        self.assertEqual(self._signup(self.kofi_user).status_code, 200)
        self.assertEqual(self._signups(), {(self.kofi.pk, 'pending')})

    def test_a_member_cannot_withdraw_someone_else(self):
        self._signup(self.esi_user)

        response = self._client(self.kofi_user).post(f'{OPPS}{self.ushers.pk}/withdraw/',
                                                      {'member_id': self.esi.pk}, format='json')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self._signups(), {(self.esi.pk, 'pending')})

    # --- sign-ups ---

    def test_a_member_sees_only_their_own_signups_and_cannot_approve_them(self):
        self._signup(self.kofi_user)
        self._signup(self.esi_user)
        client = self._client(self.kofi_user)

        rows = results(client.get(SIGNUPS))
        self.assertEqual([row['member'] for row in rows], [self.kofi.pk])
        response = client.patch(f'{SIGNUPS}{rows[0]["id"]}/', {'status': 'approved'}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._signups(), {(self.kofi.pk, 'pending'), (self.esi.pk, 'pending')})

    def test_staff_approve_and_decline_signups_with_contact_details(self):
        self._signup(self.kofi_user)
        self._signup(self.esi_user)
        client = self._client(self.admin)
        rows = {row['member']: row for row in results(client.get(SIGNUPS))}

        approved = client.patch(f'{SIGNUPS}{rows[self.kofi.pk]["id"]}/', {'status': 'approved',
                                                                         'admin_notes': 'See you Sunday.'},
                                format='json')
        client.patch(f'{SIGNUPS}{rows[self.esi.pk]["id"]}/', {'status': 'rejected'}, format='json')

        self.assertEqual(approved.status_code, 200, approved.content)
        self.assertEqual(approved.data['approved_by'], self.admin.pk)
        self.assertIsNotNone(approved.data['approved_at'])
        self.assertEqual(rows[self.kofi.pk]['member_phone'], '0201111111')
        self.assertEqual(self._row(self.admin)['spots_filled'], 1)  # the declined sign-up frees its spot
        self.assertEqual(self._row(self.kofi_user)['my_signup_status'], 'approved')

    # --- hours ---

    def test_members_cannot_record_volunteer_hours(self):
        response = self._client(self.kofi_user).post(HOURS, {
            'member': self.esi.pk, 'opportunity': self.ushers.pk, 'hours': '5.00', 'date': '2026-11-15',
        }, format='json')

        self.assertEqual(response.status_code, 403)

    def test_a_member_sees_only_their_own_hours(self):
        with tenant_context(self.church):
            VolunteerHours.objects.create(member=self.kofi, opportunity=self.ushers, hours=Decimal('3.00'),
                                          date='2026-11-15')
            VolunteerHours.objects.create(member=self.esi, opportunity=self.ushers, hours=Decimal('4.00'),
                                          date='2026-11-15')

        rows = results(self._client(self.kofi_user).get(HOURS))

        self.assertEqual([row['member'] for row in rows], [self.kofi.pk])
