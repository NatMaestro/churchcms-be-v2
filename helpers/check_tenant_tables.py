"""
Check if tables exist in a tenant schema.
"""
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure Django BEFORE importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.db import connection
from apps.churches.models import Church

def check_tables(subdomain):
    """Check if required tables exist in tenant schema."""
    try:
        church = Church.objects.get(subdomain=subdomain)
        connection.set_tenant(church)
        
        print(f"Checking tables in schema: {church.schema_name}")
        
        with connection.cursor() as cursor:
            # Check for required tables
            required_tables = ['events', 'members', 'themes', 'payments', 'announcements']
            
            for table in required_tables:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = current_schema() 
                        AND table_name = %s
                    )
                """, [table])
                exists = cursor.fetchone()[0]
                status = "✅" if exists else "❌"
                print(f"{status} {table}: {'exists' if exists else 'MISSING'}")
        
        connection.set_schema_to_public()
    except Church.DoesNotExist:
        print(f"❌ Church with subdomain '{subdomain}' not found")
    except Exception as e:
        print(f"❌ Error: {e}")
        connection.set_schema_to_public()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_tenant_tables.py <subdomain>")
        sys.exit(1)
    
    subdomain = sys.argv[1]
    check_tables(subdomain)



