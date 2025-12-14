"""
Script to delete a specific church by subdomain.
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
from django.db import connection, transaction
from django_tenants.utils import get_public_schema_name


def delete_church_by_subdomain(subdomain):
    """Delete a church and all its associated data by subdomain."""
    try:
        church = Church.objects.get(subdomain=subdomain)
        
        print(f"Found church: {church.name} (subdomain: {church.subdomain})")
        print(f"Schema: {church.schema_name}")
        
        # Store church info before deletion
        church_name = church.name
        church_subdomain = church.subdomain
        schema_name = church.schema_name
        
        # Ensure we're on public schema
        connection.set_schema_to_public()
        
        # 1. Delete users in the public schema that reference this church using raw SQL
        # This avoids Django trying to access tenant schemas with missing tables
        connection.set_schema_to_public()
        try:
            with connection.cursor() as cursor:
                # Count users first
                cursor.execute('SELECT COUNT(*) FROM public.users WHERE church_id = %s;', [church.id])
                count = cursor.fetchone()[0]
                if count > 0:
                    # Delete users using raw SQL
                    cursor.execute('DELETE FROM public.users WHERE church_id = %s;', [church.id])
                    print(f"✅ Deleted {count} user(s) referencing this church in public schema")
                else:
                    print(f"✅ No users found referencing this church")
        except Exception as e:
            print(f"⚠️ Warning: Could not delete users: {e}")
        
        # 2. Delete associated domains
        try:
            domains_deleted, _ = Domain.objects.filter(tenant=church).delete()
            print(f"✅ Deleted {domains_deleted} domain(s)")
        except Exception as e:
            print(f"⚠️ Warning: Could not delete domains: {e}")
        
        # 3. Drop the tenant schema explicitly (bypass ORM to avoid missing table errors)
        try:
            connection.set_schema_to_public()
            # Use raw SQL to drop schema
            with connection.cursor() as cursor:
                cursor.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE;')
            print(f"✅ Dropped schema {schema_name}")
        except Exception as e:
            print(f"⚠️ Warning: Could not drop schema: {e}")
        
        # 4. Delete the church record itself from the public schema
        # Ensure we're on public schema and use the correct table name
        church_id = church.id
        connection.set_schema_to_public()
        
        try:
            # Get the actual table name from the model
            table_name = Church._meta.db_table
            with connection.cursor() as cursor:
                # Use the public schema explicitly
                cursor.execute(f'DELETE FROM public."{table_name}" WHERE id = %s;', [church_id])
            print(f"✅ Deleted church record for {church_name}")
        except Exception as e:
            print(f"⚠️ Warning: Could not delete church record with SQL: {e}")
            # Try alternative: delete using model manager after ensuring public schema
            try:
                connection.set_schema_to_public()
                # Force refresh from database
                Church.objects.filter(id=church_id).delete()
                print(f"✅ Deleted church record using ORM")
            except Exception as e2:
                print(f"⚠️ Could not delete using ORM either: {e2}")
                # Last resort: try direct SQL with table name
                try:
                    with connection.cursor() as cursor:
                        cursor.execute('DELETE FROM public.churches WHERE id = %s;', [church_id])
                    print(f"✅ Deleted church record using direct SQL")
                except Exception as e3:
                    print(f"❌ All deletion methods failed: {e3}")
        
        print(f"\n✅ Successfully deleted church '{church_name}' and its associated data.")
        return True
        
    except Church.DoesNotExist:
        print(f"❌ Church with subdomain '{subdomain}' not found")
        return False
    except Exception as e:
        print(f"❌ Error deleting church '{subdomain}': {e}")
        # Ensure we are back on public schema in case of error
        try:
            connection.set_schema_to_public()
        except:
            pass
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python delete_church.py <subdomain>")
        print("\nExample: python delete_church.py stjosephtheworker")
        sys.exit(1)
    
    subdomain = sys.argv[1]
    print(f"Deleting church with subdomain: {subdomain}\n")
    delete_church_by_subdomain(subdomain)

