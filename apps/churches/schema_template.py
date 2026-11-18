"""
A ready-made, empty church schema that new churches are copied from.

Building a church schema by running every church-level migration takes over a
minute against the production database, and blocks the API while it runs.
Copying this template is a handful of catalog reads and one SQL script. After
the copy, the normal migrate runs for the new schema; the copy carries the
template's migration history, so only migrations the template is missing
actually run. A stale template therefore costs time, never correctness.

django-tenants ships a clone_schema SQL function, but it pairs indexes up by
definition and breaks on a column with both a unique key and a plain index
(members.member_id has both), so the copy is done here instead, keeping every
constraint and index name exactly as migrations created them.

If the template is missing or the copy fails, the caller falls back to building
the schema from migrations (the old, slow way).

Raw SQL is needed here: this copies schema structure, which the ORM can't express.
Every identifier comes from the Postgres catalog or from a schema name that
django-tenants has already validated, and is double-quoted.
"""
import logging

from django.core.management import call_command
from django.db import DatabaseError, connection, transaction
from django_tenants.utils import schema_exists

logger = logging.getLogger(__name__)

# Underscores can't appear in a church subdomain, so no church can ever claim this name.
TEMPLATE_SCHEMA = 'church_template'

# Indexes and key constraints are recreated by name below, so LIKE leaves them out.
LIKE_OPTIONS = ('INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING IDENTITY '
                'INCLUDING GENERATED INCLUDING STORAGE INCLUDING COMMENTS')


def refresh_template(verbosity=1):
    """Create the template if missing and migrate it to the latest."""
    connection.set_schema_to_public()
    if not schema_exists(TEMPLATE_SCHEMA):
        with connection.cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA "{TEMPLATE_SCHEMA}"')
    call_command('migrate_schemas', tenant=True, schema_name=TEMPLATE_SCHEMA,
                 interactive=False, verbosity=verbosity)
    connection.set_schema_to_public()


def _q(name):
    return '"' + name.replace('"', '""') + '"'


def _copy_script(cursor, source, target):
    """The SQL that recreates `source` as `target`: tables, keys, indexes, rows, then foreign keys."""
    # With only public on the search path, the catalog prints template objects as
    # "church_template.<name>"; pointing those at the new schema is a plain replace.
    def retarget(definition):
        return definition.replace(f'{source}.', f'{_q(target)}.')

    cursor.execute("""
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s AND c.relkind IN ('r', 'p') ORDER BY c.relname""", [source])
    tables = [row[0] for row in cursor.fetchall()]

    cursor.execute("""
        SELECT rel.relname, con.conname, con.contype, pg_get_constraintdef(con.oid)
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = rel.relnamespace
        WHERE n.nspname = %s AND con.contype IN ('p', 'u', 'x', 'f')
        ORDER BY con.contype = 'f', rel.relname, con.conname""", [source])
    constraints = cursor.fetchall()

    cursor.execute("""
        SELECT pg_get_indexdef(i.indexrelid)
        FROM pg_index i
        JOIN pg_class rel ON rel.oid = i.indrelid
        JOIN pg_namespace n ON n.oid = rel.relnamespace
        WHERE n.nspname = %s
          AND i.indexrelid NOT IN (SELECT conindid FROM pg_constraint WHERE conindid <> 0)
        ORDER BY 1""", [source])
    indexes = [row[0] for row in cursor.fetchall()]

    cursor.execute("""
        SELECT table_name, column_name FROM information_schema.columns
        WHERE table_schema = %s AND is_identity = 'YES'""", [source])
    identities = cursor.fetchall()

    src, dst = _q(source), _q(target)
    statements = [f'CREATE SCHEMA {dst}']
    statements += [f'CREATE TABLE {dst}.{_q(t)} (LIKE {src}.{_q(t)} {LIKE_OPTIONS})' for t in tables]
    statements += [f'ALTER TABLE {dst}.{_q(t)} ADD CONSTRAINT {_q(name)} {retarget(definition)}'
                   for t, name, kind, definition in constraints if kind != 'f']
    statements += [retarget(definition) for definition in indexes]
    # Rows the template holds (migration history, content types, permissions).
    statements += [f'INSERT INTO {dst}.{_q(t)} OVERRIDING SYSTEM VALUE SELECT * FROM {src}.{_q(t)}'
                   for t in tables]
    # Each table's ID counter continues after the copied rows (or starts at 1).
    statements += [
        f"SELECT setval(pg_get_serial_sequence('{dst}.{_q(t)}', '{c}'), "
        f'COALESCE((SELECT max({_q(c)}) FROM {dst}.{_q(t)}), 1), '
        f'(SELECT max({_q(c)}) FROM {dst}.{_q(t)}) IS NOT NULL)'
        for t, c in identities
    ]
    statements += [f'ALTER TABLE {dst}.{_q(t)} ADD CONSTRAINT {_q(name)} {retarget(definition)}'
                   for t, name, kind, definition in constraints if kind == 'f']
    return ';\n'.join(statements) + ';'


def copy_template_to(schema_name):
    """Copy the template into a new schema. Returns False (and leaves nothing behind) if it can't."""
    if not schema_exists(TEMPLATE_SCHEMA):
        logger.warning('church_template_missing', extra={'schema': schema_name})
        return False
    connection.set_schema_to_public()
    try:
        # A savepoint, so a failed copy leaves nothing behind and the caller's transaction usable.
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(_copy_script(cursor, TEMPLATE_SCHEMA, schema_name))
    except DatabaseError:
        logger.exception('church_template_copy_failed', extra={'schema': schema_name})
        return False
    return True
