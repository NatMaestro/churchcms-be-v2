"""
Check what tables exist in the database
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

def check_tables():
    """Check all tables in database"""
    print("\n" + "="*60)
    print("📊 DATABASE TABLES")
    print("="*60 + "\n")
    
    with connection.cursor() as cursor:
        # Get all schemas
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            ORDER BY schema_name
        """)
        schemas = [row[0] for row in cursor.fetchall()]
        
        print(f"Found {len(schemas)} schema(s):\n")
        
        for schema in schemas:
            # Get tables in this schema
            cursor.execute(f"""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = '{schema}' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"📁 SCHEMA: {schema}")
            print(f"   Tables: {len(tables)}")
            
            if tables:
                for table in tables:
                    # Count rows
                    try:
                        cursor.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
                        count = cursor.fetchone()[0]
                        print(f"   ├─ {table} ({count} rows)")
                    except:
                        print(f"   ├─ {table}")
            else:
                print(f"   └─ (No tables yet)")
            
            print()
    
    print("="*60)
    print("\n💡 NOTE:")
    print("  - 'public' schema = Shared tables (churches, users, domains)")
    print("  - Tenant schemas = Created when you run: python quickstart.py")
    print("  - Each church gets its own schema with isolated tables")
    print("\n")

if __name__ == '__main__':
    check_tables()

