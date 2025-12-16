"""
Check if a church exists and tenant schema is accessible.
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.churches.models import Church, Domain
from apps.authentication.models import User
from django.db import connection

subdomain = 'calvary'

try:
    church = Church.objects.get(subdomain=subdomain)
    print(f"✅ Church found: {church.name}")
    print(f"   Subdomain: {church.subdomain}")
    print(f"   Schema: {church.schema_name}")
    print(f"   Created: {church.created_at}")
    
    # Check domains
    domains = Domain.objects.filter(tenant=church)
    print(f"\n📋 Domains ({domains.count()}):")
    for domain in domains:
        print(f"   - {domain.domain} (primary: {domain.is_primary})")
    
    # Check tenant schema
    print(f"\n🔍 Checking tenant schema...")
    connection.set_tenant(church)
    user_count = User.objects.count()
    print(f"   Users in tenant schema: {user_count}")
    if user_count > 0:
        users = User.objects.all()[:3]
        print(f"   Sample users:")
        for user in users:
            print(f"     - {user.email} ({user.role})")
    connection.set_schema_to_public()
    print("✅ Tenant schema is accessible")
    
except Church.DoesNotExist:
    print(f"❌ Church with subdomain '{subdomain}' not found")
    print("\nAvailable churches:")
    churches = Church.objects.exclude(schema_name='public').order_by('-created_at')[:5]
    for c in churches:
        print(f"   - {c.name} ({c.subdomain})")



