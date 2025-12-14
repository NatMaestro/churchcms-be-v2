"""
Debug tenant resolution
"""
import os
import sys
import django
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django_tenants.utils import get_tenant_model, get_tenant_domain_model
from apps.churches.models import Church, Domain

def debug_tenant(hostname):
    """Debug tenant resolution for a hostname"""
    print(f"\n🔍 Debugging tenant resolution for: {hostname}\n")
    
    # Check if domain exists
    try:
        domain = Domain.objects.select_related('tenant').get(domain=hostname)
        print(f"✅ Domain found: {domain.domain}")
        print(f"   → Church: {domain.tenant.name}")
        print(f"   → Schema: {domain.tenant.schema_name}")
        print(f"   → Is Primary: {domain.is_primary}")
        return True
    except Domain.DoesNotExist:
        print(f"❌ Domain NOT found: {hostname}")
        print(f"\nAvailable domains:")
        domains = Domain.objects.all()
        for d in domains:
            print(f"   - {d.domain} → {d.tenant.name}")
        return False

if __name__ == '__main__':
    # Test hostnames
    hostnames = [
        'testchurch.lvh.me',
        'testchurch.localhost',
        'localhost',
        'testchurch.lvh.me:8000',
    ]
    
    for hostname in hostnames:
        debug_tenant(hostname)
        print()




