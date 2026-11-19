"""
New church schemas are copied from a ready-made template instead of being built
by running every migration. A copy must be indistinguishable from a migrated
schema, must use its own ID counters, and creation must still work (the slow
way) when the template can't be used.
"""
from unittest import mock

from django.db import connection
from django.test import TestCase
from django_tenants.models import TenantMixin
from django_tenants.utils import schema_context, schema_exists

from apps.churches import schema_template
from apps.churches.models import Church
from apps.churches.schema_template import TEMPLATE_SCHEMA, refresh_template
from apps.members.models import Member


def make_church(subdomain):
    return Church.objects.create(schema_name=subdomain, subdomain=subdomain, name=subdomain.title(),
                                 email=f'office@{subdomain}.example.test')


def migrated_the_slow_way(subdomain):
    """A church whose schema is built by the library from migrations, as before the template."""
    with mock.patch.object(Church, 'create_schema', TenantMixin.create_schema):
        return make_church(subdomain)


def schema_shape(schema):
    """Tables, columns, constraints, indexes and sequences, with the schema name taken out."""
    def strip(text):
        return (text or '').replace(f'"{schema}".', '').replace(f'{schema}.', '')

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name, column_name, data_type, is_nullable, column_default
            FROM information_schema.columns WHERE table_schema = %s""", [schema])
        columns = {(t, c, d, n, strip(default)) for t, c, d, n, default in cursor.fetchall()}

        cursor.execute("""
            SELECT rel.relname, con.conname, con.contype, pg_get_constraintdef(con.oid)
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace ns ON ns.oid = rel.relnamespace
            WHERE ns.nspname = %s""", [schema])
        constraints = {(t, name, kind, strip(definition)) for t, name, kind, definition in cursor.fetchall()}

        cursor.execute('SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname = %s', [schema])
        indexes = {(t, name, strip(definition)) for t, name, definition in cursor.fetchall()}

        cursor.execute("""
            SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s AND c.relkind = 'S'""", [schema])
        sequences = {row[0] for row in cursor.fetchall()}

        cursor.execute(f'SELECT app, name FROM "{schema}".django_migrations')
        migrations = set(cursor.fetchall())

    return {'columns': columns, 'constraints': constraints, 'indexes': indexes,
            'sequences': sequences, 'migrations': migrations}


class ChurchTemplateTests(TestCase):
    def setUp(self):
        connection.set_schema_to_public()
        refresh_template(verbosity=0)

    def tearDown(self):
        connection.set_schema_to_public()

    def test_a_copied_church_schema_matches_a_migrated_one(self):
        make_church('copiedchurch')
        migrated_the_slow_way('migratedchurch')

        copied, migrated = schema_shape('copiedchurch'), schema_shape('migratedchurch')

        for part in migrated:
            with self.subTest(part=part):
                self.assertTrue(migrated[part])
                self.assertEqual(copied[part], migrated[part])

    def test_a_copied_church_uses_its_own_id_counters(self):
        make_church('copiedchurch')

        defaults = schema_shape('copiedchurch')['columns']
        self.assertFalse([d for d in defaults if TEMPLATE_SCHEMA in d[4]])

        with schema_context('copiedchurch'):
            Member.objects.create(member_id='C-0001', first_name='Ama', last_name='Copy',
                                  email='ama@copied.example.test')
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT count(*) FROM "{TEMPLATE_SCHEMA}".members')
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_a_copied_church_has_none_of_another_churchs_data(self):
        first = make_church('firstchurch')
        with schema_context(first.schema_name):
            Member.objects.create(member_id='F-0001', first_name='Only', last_name='InFirst',
                                  email='only@first.example.test')

        second = make_church('secondchurch')

        with schema_context(second.schema_name):
            self.assertFalse(Member.objects.exists())

    def test_the_template_is_used_when_it_is_there(self):
        with mock.patch.object(TenantMixin, 'create_schema') as slow_way:
            make_church('copiedchurch')

        slow_way.assert_not_called()
        self.assertTrue(schema_exists('copiedchurch'))

    def test_without_a_template_the_church_is_built_from_migrations(self):
        with mock.patch.object(schema_template, 'TEMPLATE_SCHEMA', 'no_such_template'):
            church = make_church('fallbackchurch')

        self.assertEqual(schema_shape(church.schema_name), schema_shape(TEMPLATE_SCHEMA))

    def test_a_failed_copy_falls_back_and_leaves_the_transaction_usable(self):
        with mock.patch.object(schema_template, '_copy_script',
                               return_value='CREATE SCHEMA "fallbackchurch"; SELECT no_such_function();'):
            church = make_church('fallbackchurch')

        self.assertEqual(schema_shape(church.schema_name), schema_shape(TEMPLATE_SCHEMA))
        self.assertTrue(Church.objects.filter(subdomain='fallbackchurch').exists())

    def test_refreshing_an_up_to_date_template_changes_nothing(self):
        before = schema_shape(TEMPLATE_SCHEMA)

        refresh_template(verbosity=0)

        self.assertEqual(schema_shape(TEMPLATE_SCHEMA), before)
