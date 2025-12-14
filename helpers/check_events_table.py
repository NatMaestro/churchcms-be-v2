"""
Check if events table exists in tenant schemas
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django_tenants.utils import schema_context
from apps.churches.models import Church

def check_tables(tenant):
    """Check what tables exist in a tenant schema."""
    with schema_context(tenant.schema_name):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = %s
                ORDER BY tablename;
            """, [tenant.schema_name])
            
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"\n{'='*60}")
            print(f"Tables in {tenant.name} ({tenant.schema_name}):")
            print(f"{'='*60}")
            
            # Check for expected tables
            expected = ['events', 'event_registrations', 'members', 'payments', 'announcements']
            for table in expected:
                if table in tables:
                    print(f"  ✅ {table}")
                else:
                    print(f"  ❌ {table} - MISSING!")
            
            print(f"\n  Total tables: {len(tables)}")
            print(f"  All tables: {', '.join(tables[:10])}...")

if __name__ == "__main__":
    churches = Church.objects.exclude(schema_name='public')
    
    for church in churches:
        check_tables(church)




