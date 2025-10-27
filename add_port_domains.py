"""
Add domains with port numbers
"""
import os
import sys
import django
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.churches.models import Church, Domain

churches = Church.objects.exclude(schema_name='public')

for church in churches:
    # Add with :8000 port
    Domain.objects.get_or_create(
        domain=f'{church.subdomain}.lvh.me:8000',
        defaults={'tenant': church, 'is_primary': False}
    )
    
    Domain.objects.get_or_create(
        domain=f'{church.subdomain}.localhost:8000',
        defaults={'tenant': church, 'is_primary': False}
    )

print('\n✅ Added all port-specific domains!')
print('\nAvailable URLs:')
for church in churches:
    print(f'  http://{church.subdomain}.lvh.me:8000/api/docs/')

