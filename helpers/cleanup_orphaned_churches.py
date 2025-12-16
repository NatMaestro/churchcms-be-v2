"""
Cleanup script to find and delete orphaned churches (churches without users).
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.churches.models import Church, Domain
from apps.authentication.models import User
from django.db import connection
from django_tenants.utils import get_public_schema_name


def find_orphaned_churches():
    """Find churches that have no users in their tenant schema."""
    public_schema = get_public_schema_name()
    churches = Church.objects.exclude(schema_name=public_schema)
    orphaned = []
    
    print(f"Checking {churches.count()} churches for orphaned status...\n")
    
    for church in churches:
        try:
            # Switch to tenant schema
            connection.set_tenant(church)
            
            # Check if there are any users
            user_count = User.objects.count()
            
            # Switch back to public schema
            connection.set_schema_to_public()
            
            if user_count == 0:
                orphaned.append(church)
                print(f"  ❌ {church.name} (subdomain: {church.subdomain}) - No users found")
            else:
                print(f"  ✅ {church.name} (subdomain: {church.subdomain}) - {user_count} user(s)")
                
        except Exception as e:
            connection.set_schema_to_public()
            print(f"  ⚠️  {church.name} (subdomain: {church.subdomain}) - Error: {str(e)}")
            # If we can't access the schema, consider it orphaned
            orphaned.append(church)
    
    return orphaned


def delete_orphaned_churches(orphaned_churches, dry_run=True):
    """Delete orphaned churches and their domains."""
    if not orphaned_churches:
        print("\n✅ No orphaned churches found!")
        return
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Found {len(orphaned_churches)} orphaned church(es):")
    for church in orphaned_churches:
        print(f"  - {church.name} (subdomain: {church.subdomain}, schema: {church.schema_name})")
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No churches will be deleted.")
        print("   Run with --delete flag to actually delete them.")
        return
    
    print("\n🗑️  Deleting orphaned churches...")
    
    for church in orphaned_churches:
        try:
            # Delete all domains associated with this church
            domains = Domain.objects.filter(tenant=church)
            domain_count = domains.count()
            domains.delete()
            print(f"  ✅ Deleted {domain_count} domain(s) for {church.name}")
            
            # Delete the church (this will also drop the schema)
            church_name = church.name
            church_subdomain = church.subdomain
            church.delete()
            print(f"  ✅ Deleted church: {church_name} (subdomain: {church_subdomain})")
            
        except Exception as e:
            print(f"  ❌ Error deleting {church.name}: {str(e)}")
    
    print("\n✅ Cleanup complete!")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Find and delete orphaned churches')
    parser.add_argument('--delete', action='store_true', help='Actually delete orphaned churches (default is dry run)')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Orphaned Church Cleanup Script")
    print("=" * 60)
    
    orphaned = find_orphaned_churches()
    delete_orphaned_churches(orphaned, dry_run=not args.delete)



