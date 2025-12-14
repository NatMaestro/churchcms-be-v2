"""
Check if tables exist in tenant schema.
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from apps.churches.models import Church

def check_tables(subdomain):
    """Check if tables exist in tenant schema."""
    try:
        church = Church.objects.get(subdomain=subdomain)
        print(f"Found church: {church.name} (schema: {church.schema_name})")
        
        # Switch to tenant schema
        connection.set_tenant(church)
        print(f"Switched to tenant schema: {church.schema_name}")
        
        # Check tables
        tables_to_check = ['members', 'payments', 'events', 'announcements']
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = current_schema() 
                AND table_name = ANY(%s)
                ORDER BY table_name
            """, [tables_to_check])
            
            existing_tables = [row[0] for row in cursor.fetchall()]
            missing_tables = [t for t in tables_to_check if t not in existing_tables]
            
            print(f"\n✅ Existing tables: {', '.join(existing_tables) if existing_tables else 'None'}")
            if missing_tables:
                print(f"❌ Missing tables: {', '.join(missing_tables)}")
            else:
                print("✅ All tables exist!")
        
        # Switch back to public
        connection.set_schema_to_public()
        
    except Church.DoesNotExist:
        print(f"❌ Church with subdomain '{subdomain}' not found")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        connection.set_schema_to_public()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_tables.py <subdomain>")
        sys.exit(1)
    
    subdomain = sys.argv[1]
    check_tables(subdomain)
