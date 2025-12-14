"""
Check if tables exist in tenant schemas.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from apps.churches.models import Church

def check_tables():
    """Check which tables exist in the olamchurch tenant."""
    
    church = Church.objects.get(subdomain='olamchurch')
    print(f"\nChecking tables for: {church.name} (schema: {church.schema_name})")
    
    # Set schema
    with connection.cursor() as cursor:
        cursor.execute(f"SET search_path TO {church.schema_name}")
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = %s
            ORDER BY tablename;
        """, [church.schema_name])
        
        tables = cursor.fetchall()
        
        print(f"\nFound {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Check specific tables
        required_tables = ['themes', 'events', 'announcements', 'notifications', 'members']
        print(f"\nChecking required tables:")
        for table in required_tables:
            exists = any(t[0] == table for t in tables)
            status = "✅" if exists else "❌"
            print(f"  {status} {table}")

if __name__ == '__main__':
    check_tables()



