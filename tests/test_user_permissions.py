"""
/api/v1/auth/users/ used to allow any logged-in member to edit any user in
their church, including their own `role` (to "superadmin") and `church`.
"""
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from apps.authentication.models import User
from apps.churches.models import Church

USERS_URL = '/api/v1/auth/users/'


def make_church(subdomain):
    # These tests only need the church rows, not their Postgres schemas.
    with mock.patch.object(Church, 'auto_create_schema', False):
        return Church.objects.create(
            schema_name=subdomain, subdomain=subdomain, name=subdomain.title(),
            email=f'office@{subdomain}.example.test',
        )


class UserEndpointPermissionTests(TestCase):
    def setUp(self):
        self.church = make_church('alpha')
        self.other_church = make_church('beta')
        self.admin = User.objects.create_user(
            email='admin@alpha.test', password='pass-12345', name='Alpha Admin',
            church=self.church, role='admin',
        )
        self.member = User.objects.create_user(
            email='member@alpha.test', password='pass-12345', name='Alpha Member',
            church=self.church, role='member',
        )
        self.other_admin = User.objects.create_user(
            email='admin@beta.test', password='pass-12345', name='Beta Admin',
            church=self.other_church, role='admin',
        )

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    # --- members -------------------------------------------------------------

    def test_member_cannot_promote_themselves_to_superadmin(self):
        response = self.client_for(self.member).patch(
            f'{USERS_URL}{self.member.id}/', {'role': 'superadmin'}, format='json'
        )

        self.assertEqual(response.status_code, 403)
        self.member.refresh_from_db()
        self.assertEqual(self.member.role, 'member')

    def test_member_cannot_change_the_admins_password(self):
        response = self.client_for(self.member).patch(
            f'{USERS_URL}{self.admin.id}/', {'password': 'attacker-pass-1'}, format='json'
        )

        self.assertIn(response.status_code, (403, 404))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('pass-12345'))

    def test_member_cannot_create_or_delete_users(self):
        client = self.client_for(self.member)

        create = client.post(USERS_URL, {
            'email': 'new@alpha.test', 'name': 'New', 'password': 'pass-12345', 'role': 'admin',
        }, format='json')
        delete = client.delete(f'{USERS_URL}{self.admin.id}/')

        self.assertEqual(create.status_code, 403)
        self.assertIn(delete.status_code, (403, 404))
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())
        self.assertFalse(User.objects.filter(email='new@alpha.test').exists())

    def test_member_can_read_only_their_own_record(self):
        client = self.client_for(self.member)

        listing = client.get(USERS_URL)
        own = client.get(f'{USERS_URL}{self.member.id}/')
        other = client.get(f'{USERS_URL}{self.admin.id}/')

        self.assertEqual([u['id'] for u in listing.data['results']], [self.member.id])
        self.assertEqual(own.status_code, 200)
        self.assertEqual(other.status_code, 404)

    # --- church admins -------------------------------------------------------

    def test_admin_cannot_grant_superadmin(self):
        response = self.client_for(self.admin).patch(
            f'{USERS_URL}{self.member.id}/', {'role': 'superadmin'}, format='json'
        )

        self.assertEqual(response.status_code, 400)
        self.member.refresh_from_db()
        self.assertEqual(self.member.role, 'member')

    def test_admin_can_promote_member_to_admin(self):
        response = self.client_for(self.admin).patch(
            f'{USERS_URL}{self.member.id}/', {'role': 'admin'}, format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.member.refresh_from_db()
        self.assertEqual(self.member.role, 'admin')

    def test_church_field_cannot_be_changed_through_the_api(self):
        self.client_for(self.admin).patch(
            f'{USERS_URL}{self.member.id}/', {'church': self.other_church.id}, format='json'
        )

        self.member.refresh_from_db()
        self.assertEqual(self.member.church_id, self.church.id)

    def test_admin_created_user_always_belongs_to_the_admins_church(self):
        response = self.client_for(self.admin).post(USERS_URL, {
            'email': 'new@alpha.test', 'name': 'New', 'password': 'pass-12345',
            'role': 'member', 'church': self.other_church.id,
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.get(email='new@alpha.test').church_id, self.church.id)

    def test_admin_cannot_see_or_edit_users_of_another_church(self):
        client = self.client_for(self.admin)

        listing = client.get(USERS_URL)
        edit = client.patch(
            f'{USERS_URL}{self.other_admin.id}/', {'name': 'Hijacked'}, format='json'
        )

        self.assertNotIn(self.other_admin.id, [u['id'] for u in listing.data['results']])
        self.assertEqual(edit.status_code, 404)
