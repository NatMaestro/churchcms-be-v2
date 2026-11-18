"""
Create or update the empty church schema that new churches are copied from.
Run on every deploy, after migrate_schemas (see render.yaml).

    python manage.py refresh_church_template
"""
from django.core.management.base import BaseCommand

from apps.churches.schema_template import TEMPLATE_SCHEMA, refresh_template


class Command(BaseCommand):
    help = 'Create or migrate the template schema that new church schemas are copied from'

    def handle(self, *args, **options):
        refresh_template(verbosity=options['verbosity'])
        self.stdout.write(self.style.SUCCESS(f'Church template "{TEMPLATE_SCHEMA}" is up to date.'))
