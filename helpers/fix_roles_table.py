#!/usr/bin/env python
"""
Fix roles table in tenant schema.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from apps.churches.models import Church

def fix_roles_table(schema_name):
    """Fix roles table in tenant schema."""
    try:
        # Get the church/tenant
        church = Church.objects.get(subdomain=schema_name)
        connection.set_tenant(church)
        
        # Check if table exists
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = current_schema() 
                    AND table_name = 'roles'
                )
            """)
            exists = cursor.fetchone()[0]
            
            if exists:
                print(f"✅ roles table exists in schema '{schema_name}'")
                return
            
            print(f"❌ roles table does NOT exist in schema '{schema_name}'")
            print("Creating roles table...")
            
            # Create the table manually
            cursor.execute("""
                CREATE TABLE roles (
                    id BIGSERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT NOT NULL,
                    permissions JSONB DEFAULT '[]'::jsonb,
                    color VARCHAR(50) DEFAULT 'blue',
                    icon VARCHAR(50) DEFAULT 'Shield',
                    is_default BOOLEAN DEFAULT FALSE,
                    is_system_role BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create permissions table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = current_schema() 
                    AND table_name = 'permissions'
                )
            """)
            perm_exists = cursor.fetchone()[0]
            
            if not perm_exists:
                print("Creating permissions table...")
                cursor.execute("""
                    CREATE TABLE permissions (
                        id BIGSERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        code VARCHAR(100) NOT NULL UNIQUE,
                        resource VARCHAR(50) NOT NULL,
                        action VARCHAR(20) NOT NULL,
                        description TEXT NOT NULL,
                        is_system_permission BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(resource, action)
                    )
                """)
                cursor.execute("CREATE INDEX permissions_code_idx ON permissions(code)")
            
            # Create user_roles table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = current_schema() 
                    AND table_name = 'user_roles'
                )
            """)
            user_role_exists = cursor.fetchone()[0]
            
            if not user_role_exists:
                print("Creating user_roles table...")
                # Get the auth_user table name
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user_table = User._meta.db_table
                
                cursor.execute(f"""
                    CREATE TABLE user_roles (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL REFERENCES {user_table}(id) ON DELETE CASCADE,
                        role_id BIGINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                        assigned_by_id BIGINT REFERENCES {user_table}(id) ON DELETE SET NULL,
                        assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        expires_at TIMESTAMP WITH TIME ZONE,
                        UNIQUE(user_id, role_id)
                    )
                """)
            
            print(f"✅ Successfully created roles tables in schema '{schema_name}'")
            
    except Church.DoesNotExist:
        print(f"❌ Church with subdomain '{schema_name}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python fix_roles_table.py <schema_name>")
        sys.exit(1)
    
    schema_name = sys.argv[1]
    fix_roles_table(schema_name)


