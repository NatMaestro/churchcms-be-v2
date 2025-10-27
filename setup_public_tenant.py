"""
Setup public tenant for localhost access
"""
import os
import sys
import django
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.churches.models import Church, Domain
from django.db import connection

def setup_public_tenant():
    """Create public tenant for localhost access"""
    print("\n🔧 Setting up public tenant for localhost...")
    
    connection.set_schema_to_public()
    
    # Check if public tenant exists
    public_tenant = Church.objects.filter(schema_name='public').first()
    
    if not public_tenant:
        print("\nCreating public tenant...")
        public_tenant = Church.objects.create(
            schema_name='public',
            name='Public',
            subdomain='public',
            email='public@faithflows.com',
            is_active=True
        )
        print(f"✅ Created public tenant")
    else:
        print(f"✅ Public tenant already exists")
    
    # Create localhost domains
    domains_to_create = [
        ('localhost', True),
        ('127.0.0.1', False),
        ('localhost:8000', False),
        ('127.0.0.1:8000', False),
    ]
    
    print("\nCreating domains...")
    for domain_name, is_primary in domains_to_create:
        domain, created = Domain.objects.get_or_create(
            domain=domain_name,
            defaults={
                'tenant': public_tenant,
                'is_primary': is_primary
            }
        )
        status = "✅ Created" if created else "ℹ️  Already exists"
        print(f"  {status}: {domain_name}")
    
    print("\n" + "="*60)
    print("✅ PUBLIC TENANT SETUP COMPLETE!")
    print("="*60)
    print("\nYou can now access:")
    print("  http://localhost:8000/api/docs/")
    print("  http://127.0.0.1:8000/api/docs/")
    print("\n")

if __name__ == '__main__':
    setup_public_tenant()

