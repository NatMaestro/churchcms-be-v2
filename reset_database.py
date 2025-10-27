"""
Reset database - Drop all tables and schemas, then recreate fresh
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def reset_database():
    """Drop all schemas and tables"""
    print("\n" + "="*60)
    print("🔥 RESETTING DATABASE")
    print("="*60 + "\n")
    
    with connection.cursor() as cursor:
        # Get all schemas (except system schemas)
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            AND schema_name NOT LIKE 'pg_temp%'
            AND schema_name NOT LIKE 'pg_toast%'
            ORDER BY schema_name
        """)
        schemas = [row[0] for row in cursor.fetchall()]
        
        print(f"Found {len(schemas)} schema(s) to drop:\n")
        
        for schema in schemas:
            print(f"🗑️  Dropping schema: {schema}")
            try:
                cursor.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
                print(f"   ✅ Dropped: {schema}")
            except Exception as e:
                print(f"   ⚠️  Error dropping {schema}: {e}")
        
        print("\n" + "="*60)
        print("✅ DATABASE RESET COMPLETE!")
        print("="*60)
        print("\n📋 Next steps:")
        print("  1. python manage.py migrate_schemas --shared")
        print("  2. python manage.py migrate_schemas")
        print("  3. python seed_database.py")
        print("\n")

if __name__ == '__main__':
    confirm = input("⚠️  This will DELETE ALL DATA. Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        reset_database()
    else:
        print("❌ Cancelled")

