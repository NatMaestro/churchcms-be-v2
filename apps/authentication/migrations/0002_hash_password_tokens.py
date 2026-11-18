"""
Data only: replace each stored password token with its SHA-256 hash, so links
already emailed (holding the raw token) keep working once lookups hash the
token. No schema change; the 64-character hex hash fits the existing column.

Not reversible: a hash can't be turned back into its token. Reversing is a
no-op, so after a rollback, links issued before this migration stop working
and people request a new one.
"""
import hashlib

from django.db import migrations

BATCH_SIZE = 500
SHA256_HEX_LENGTH = 64


def hash_existing_tokens(apps, schema_editor):
    PasswordResetToken = apps.get_model('authentication', 'PasswordResetToken')
    batch = []
    for row in PasswordResetToken.objects.only('id', 'token').iterator(chunk_size=BATCH_SIZE):
        # Raw tokens are 43-character URL-safe strings, never 64 hex characters.
        if len(row.token) == SHA256_HEX_LENGTH:
            continue
        row.token = hashlib.sha256(row.token.encode()).hexdigest()
        batch.append(row)
        if len(batch) >= BATCH_SIZE:
            PasswordResetToken.objects.bulk_update(batch, ['token'])
            batch = []
    if batch:
        PasswordResetToken.objects.bulk_update(batch, ['token'])


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(hash_existing_tokens, migrations.RunPython.noop),
    ]
