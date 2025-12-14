"""
Fix tenant schema by ensuring all migrations are applied and tables exist.
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
from django.core.management import call_command
from apps.churches.models import Church

def fix_tenant_schema(subdomain):
    """Fix a tenant schema by running migrations."""
    try:
        church = Church.objects.get(subdomain=subdomain)
        print(f"Found church: {church.name} (schema: {church.schema_name})")
        
        # Switch to tenant schema
        connection.set_tenant(church)
        print(f"Switched to tenant schema: {church.schema_name}")
        
        # Check multiple tables
        tables_to_check = ['members', 'service_requests', 'prayer_requests', 'events', 'payments']
        missing_tables = []
        
        for table_name in tables_to_check:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = current_schema() 
                    AND table_name = %s
                """, [table_name])
                table_exists = bool(cursor.fetchone())
                
                if not table_exists:
                    missing_tables.append(table_name)
                    print(f"❌ {table_name} table does not exist")
                else:
                    print(f"✅ {table_name} table exists")
        
        if missing_tables:
            print(f"\n⚠️  Missing tables: {', '.join(missing_tables)}. Running migrations...")
            
            # Run migrations with --fake-initial to create tables
            try:
                call_command('migrate', '--fake-initial', verbosity=1)
                print("✅ Migrations applied with --fake-initial")
            except Exception as e:
                print(f"⚠️  Error with --fake-initial: {e}")
                # Try regular migrate
                try:
                    call_command('migrate', verbosity=1)
                    print("✅ Migrations applied")
                except Exception as e2:
                    print(f"❌ Error applying migrations: {e2}")
                    # Try to reset migrations for missing apps
                    print("Attempting to reset migration state...")
                    with connection.cursor() as cursor:
                        # Delete migration records for missing apps
                        app_map = {
                            'members': 'members',
                            'service_requests': 'requests',
                            'prayer_requests': 'prayers',
                            'events': 'events',
                            'payments': 'payments'
                        }
                        for table, app in app_map.items():
                            if table in missing_tables:
                                cursor.execute("""
                                    DELETE FROM django_migrations 
                                    WHERE app = %s
                                """, [app])
                    # Now run migrations fresh
                    call_command('migrate', verbosity=1)
                    print("✅ Migrations reset and reapplied")
        
        # Verify all tables exist now
        print("\n📋 Verifying all tables...")
        all_exist = True
        for table_name in tables_to_check:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = current_schema() 
                    AND table_name = %s
                """, [table_name])
                table_exists = bool(cursor.fetchone())
                
                if table_exists:
                    print(f"  ✅ {table_name}")
                else:
                    print(f"  ❌ {table_name} still missing")
                    all_exist = False
        
        if all_exist:
            print("\n✅ Schema fixed successfully!")
        else:
            print("\n⚠️  Some tables are still missing. You may need to run migrations manually.")
        
        # Switch back to public
        connection.set_schema_to_public()
        
    except Church.DoesNotExist:
        print(f"❌ Church with subdomain '{subdomain}' not found")
    except Exception as e:
        print(f"❌ Error: {e}")
        connection.set_schema_to_public()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python fix_tenant_schema.py <subdomain>")
        sys.exit(1)
    
    subdomain = sys.argv[1]
    fix_tenant_schema(subdomain)

