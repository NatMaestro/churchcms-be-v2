"""
Seed database with data from frontend db.json
This will populate your Django database with all the existing data.

Usage:
    python seed_database.py
"""

import os
import sys
import django
import json
from pathlib import Path
from datetime import datetime
from django.utils import timezone

# Setup Django
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.churches.models import Church, Domain
from apps.authentication.models import User
from apps.members.models import Member
from apps.events.models import Event, EventRegistration
from apps.payments.models import Payment, Pledge
from apps.ministries.models import Ministry, MinistryMembership
from apps.announcements.models import Announcement
from apps.requests.models import ServiceRequest
from apps.roles.models import Role, Permission, UserRole
from apps.notifications.models import Notification
from apps.themes.models import Theme
from django.db import connection, transaction


# Path to db.json
DB_JSON_PATH = Path(__file__).parent.parent / 'faithflow-studio' / 'db.json'


def load_json_data():
    """Load data from db.json"""
    print(f"📂 Loading data from: {DB_JSON_PATH}")
    
    if not DB_JSON_PATH.exists():
        print(f"❌ Error: db.json not found at {DB_JSON_PATH}")
        sys.exit(1)
    
    with open(DB_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✅ Loaded data with {len(data)} collections")
    return data


def parse_datetime(date_string):
    """Parse datetime string to timezone-aware datetime"""
    if not date_string:
        return timezone.now()
    try:
        # Try parsing ISO format
        dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
    except:
        return timezone.now()


def seed_churches(churches_data):
    """Seed churches and domains"""
    print("\n🏢 Seeding Churches...")
    
    created_churches = {}
    
    for church_data in churches_data:
        subdomain = church_data.get('subdomain', 'default')
        
        # Create or update church
        church, created = Church.objects.update_or_create(
            subdomain=subdomain,
            defaults={
                'name': church_data.get('name', 'Unknown Church'),
                'schema_name': subdomain,  # For multi-tenancy
                'email': church_data.get('email', ''),
                'phone': church_data.get('phone', ''),
                'address': church_data.get('address', ''),
                'denomination': church_data.get('denomination', ''),
                'website': church_data.get('website', ''),
                'plan': church_data.get('plan', 'trial'),
                'is_active': church_data.get('isActive', True),
                
                # Settings as JSON
                'branding_settings': church_data.get('brandingSettings', {}),
                'payment_settings': church_data.get('paymentSettings', {}),
                'member_settings': church_data.get('memberSettings', {}),
                'communication_settings': church_data.get('communicationSettings', {}),
                'privacy_settings': church_data.get('privacySettings', {}),
                'automation_settings': church_data.get('automationSettings', {}),
                'integration_settings': church_data.get('integrationSettings', {}),
                'features': church_data.get('features', {}),
            }
        )
        
        action = "Created" if created else "Updated"
        print(f"  {action}: {church.name} ({subdomain})")
        
        # Create domain for the church
        domain_name = f"{subdomain}.localhost"
        domain, domain_created = Domain.objects.update_or_create(
            domain=domain_name,
            defaults={
                'tenant': church,
                'is_primary': True
            }
        )
        
        if domain_created:
            print(f"    ✓ Domain: {domain_name}")
        
        created_churches[church_data.get('id')] = church
    
    print(f"✅ Seeded {len(created_churches)} churches")
    return created_churches


def seed_users(users_data, churches_map):
    """Seed users"""
    print("\n👥 Seeding Users...")
    
    created_users = {}
    
    for user_data in users_data:
        church_id = user_data.get('churchId')
        
        # Skip superadmins for now (they don't have a church)
        if user_data.get('role') == 'superadmin' or not church_id:
            continue
        
        church = churches_map.get(church_id)
        if not church:
            print(f"  ⚠ Skipping user {user_data.get('email')} - church not found")
            continue
        
        email = user_data.get('email')
        
        # Create or update user
        user, created = User.objects.update_or_create(
            email=email,
            defaults={
                'name': user_data.get('name', ''),
                'church': church,
                'role': user_data.get('role', 'member'),
                'is_active': user_data.get('isActive', True),
            }
        )
        
        # Set password (in production, use proper password hashing)
        if created:
            password = user_data.get('password', 'password123')
            user.set_password(password)
            user.save()
        
        action = "Created" if created else "Updated"
        print(f"  {action}: {user.name} ({email}) - {church.name}")
        
        created_users[user_data.get('id')] = user
    
    print(f"✅ Seeded {len(created_users)} users")
    return created_users


def seed_themes(themes_data, churches_map):
    """Seed themes"""
    print("\n🎨 Seeding Themes...")
    
    count = 0
    for theme_data in themes_data:
        church_id = theme_data.get('churchId')
        church = churches_map.get(church_id)
        
        if not church:
            continue
        
        # Switch to tenant schema
        connection.set_tenant(church)
        
        # Get the theme data as-is (it's already in the correct JSON format)
        theme_info = theme_data.get('theme', {})
        
        theme, created = Theme.objects.update_or_create(
            church=church,
            defaults={
                'theme': theme_info,  # Store entire theme as JSON
                'is_active': True,
            }
        )
        
        if created:
            count += 1
            theme_name = theme_info.get('name', 'Default Theme')
            print(f"  Created: {theme_name} for {church.name}")
    
    print(f"✅ Seeded {count} themes")


def seed_members(members_data, churches_map, users_map):
    """Seed members"""
    print("\n👤 Seeding Members...")
    
    created_members = {}
    
    for member_data in members_data:
        church_id = member_data.get('churchId')
        church = churches_map.get(church_id)
        
        if not church:
            continue
        
        # Switch to tenant schema
        connection.set_tenant(church)
        
        member, created = Member.objects.update_or_create(
            member_id=member_data.get('memberId', member_data.get('id')),
            defaults={
                'first_name': member_data.get('firstName', ''),
                'last_name': member_data.get('lastName', ''),
                'email': member_data.get('email', ''),
                'phone': member_data.get('phone', ''),
                'date_of_birth': member_data.get('dateOfBirth'),
                'gender': member_data.get('gender', 'Other'),
                'address': member_data.get('address', ''),
                'occupational_status': member_data.get('occupation', ''),  # Use correct field name
                'profession': member_data.get('occupation', ''),  # Also store in profession
                'status': member_data.get('status', 'active'),
                'sacraments': member_data.get('sacraments', {}),
                'notes': member_data.get('notes', ''),
                # Store extra data in denomination_specific_data JSON field
                'denomination_specific_data': {
                    'maritalStatus': member_data.get('maritalStatus', ''),
                    'photo': member_data.get('photo', ''),
                    'emergencyContact': member_data.get('emergencyContact', {}),
                }
            }
        )
        
        if created:
            print(f"  Created: {member.first_name} {member.last_name} - {church.name}")
        
        created_members[member_data.get('id')] = member
    
    print(f"✅ Seeded {len(created_members)} members")
    return created_members


def seed_events(events_data, churches_map):
    """Seed events"""
    print("\n📅 Seeding Events...")
    
    count = 0
    for event_data in events_data:
        church_id = event_data.get('churchId')
        church = churches_map.get(church_id)
        
        if not church:
            continue
        
        # Switch to tenant schema
        connection.set_tenant(church)
        
        event, created = Event.objects.update_or_create(
            name=event_data.get('name'),
            date=parse_datetime(event_data.get('date')),
            church=church,
            defaults={
                'description': event_data.get('description', ''),
                'type': event_data.get('type', 'other'),
                'location': event_data.get('location', ''),
                'capacity': event_data.get('capacity', 0),
                'registration_required': event_data.get('registrationRequired', False),
                'is_recurring': event_data.get('isRecurring', False),
                'recurrence_rule': event_data.get('recurrenceRule', ''),
                'status': event_data.get('status', 'scheduled'),
            }
        )
        
        if created:
            count += 1
    
    print(f"✅ Seeded {count} events")


def seed_announcements(announcements_data, churches_map, users_map):
    """Seed announcements"""
    print("\n📢 Seeding Announcements...")
    
    count = 0
    for announcement_data in announcements_data:
        church_id = announcement_data.get('churchId')
        church = churches_map.get(church_id)
        
        if not church:
            continue
        
        # Switch to tenant schema
        connection.set_tenant(church)
        
        created_by_id = announcement_data.get('createdBy')
        created_by = users_map.get(created_by_id) if created_by_id else None
        
        announcement, created = Announcement.objects.update_or_create(
            title=announcement_data.get('title'),
            church=church,
            defaults={
                'content': announcement_data.get('content', ''),
                'priority': announcement_data.get('priority', 'normal'),
                'target_audience': announcement_data.get('targetAudience', 'all'),
                'is_active': announcement_data.get('isActive', True),
                'start_date': parse_datetime(announcement_data.get('startDate')),
                'end_date': parse_datetime(announcement_data.get('endDate')) if announcement_data.get('endDate') else None,
                'created_by': created_by,
            }
        )
        
        if created:
            count += 1
    
    print(f"✅ Seeded {count} announcements")


def seed_ministries(ministries_data, churches_map, users_map):
    """Seed ministries"""
    print("\n⛪ Seeding Ministries...")
    
    count = 0
    for ministry_data in ministries_data:
        church_id = ministry_data.get('churchId')
        church = churches_map.get(church_id)
        
        if not church:
            continue
        
        # Switch to tenant schema
        connection.set_tenant(church)
        
        leader_id = ministry_data.get('leaderId')
        leader = users_map.get(leader_id) if leader_id else None
        
        ministry, created = Ministry.objects.update_or_create(
            name=ministry_data.get('name'),
            church=church,
            defaults={
                'description': ministry_data.get('description', ''),
                'category': ministry_data.get('category', 'other'),
                'leader': leader,
                'is_active': ministry_data.get('isActive', True),
            }
        )
        
        if created:
            count += 1
    
    print(f"✅ Seeded {count} ministries")


def seed_payments(payments_data, churches_map, members_map):
    """Seed payments"""
    print("\n💰 Seeding Payments...")
    
    count = 0
    for payment_data in payments_data:
        church_id = payment_data.get('churchId')
        church = churches_map.get(church_id)
        
        if not church:
            continue
        
        # Switch to tenant schema
        connection.set_tenant(church)
        
        member_id = payment_data.get('memberId')
        member = members_map.get(member_id) if member_id else None
        
        if not member:
            continue
        
        payment, created = Payment.objects.update_or_create(
            reference=payment_data.get('reference', payment_data.get('id')),
            defaults={
                'member': member,
                'church': church,
                'amount': payment_data.get('amount', 0),
                'payment_type': payment_data.get('type', 'offering'),
                'method': payment_data.get('method', 'cash'),
                'date': parse_datetime(payment_data.get('date')),
                'notes': payment_data.get('notes', ''),
            }
        )
        
        if created:
            count += 1
    
    print(f"✅ Seeded {count} payments")


def seed_requests(requests_data, churches_map, members_map, users_map):
    """Seed service requests"""
    print("\n📋 Seeding Service Requests...")
    
    count = 0
    for request_data in requests_data:
        church_id = request_data.get('churchId')
        church = churches_map.get(church_id)
        
        if not church:
            continue
        
        # Switch to tenant schema
        connection.set_tenant(church)
        
        member_id = request_data.get('memberId')
        member = members_map.get(member_id) if member_id else None
        
        assigned_to_id = request_data.get('assignedTo')
        assigned_to = users_map.get(assigned_to_id) if assigned_to_id else None
        
        if not member:
            continue
        
        service_request, created = ServiceRequest.objects.update_or_create(
            member=member,
            request_type=request_data.get('type', 'other'),
            created_at=parse_datetime(request_data.get('createdAt')),
            defaults={
                'church': church,
                'description': request_data.get('description', ''),
                'priority': request_data.get('priority', 'normal'),
                'status': request_data.get('status', 'pending'),
                'assigned_to': assigned_to,
                'notes': request_data.get('notes', ''),
            }
        )
        
        if created:
            count += 1
    
    print(f"✅ Seeded {count} service requests")


def main():
    """Main seeding function"""
    print("="*60)
    print("🌱 FAITHFLOW DATABASE SEEDING")
    print("="*60)
    
    # Load data
    data = load_json_data()
    
    try:
        with transaction.atomic():
            # Seed in order (respecting foreign keys)
            churches_map = seed_churches(data.get('churches', []))
            users_map = seed_users(data.get('users', []), churches_map)
            
            # Seed tenant-specific data
            seed_themes(data.get('themes', []), churches_map)
            members_map = seed_members(data.get('members', []), churches_map, users_map)
            seed_events(data.get('events', []), churches_map)
            seed_announcements(data.get('announcements', []), churches_map, users_map)
            seed_ministries(data.get('ministries', []), churches_map, users_map)
            seed_payments(data.get('payments', []), churches_map, members_map)
            seed_requests(data.get('requests', []), churches_map, members_map, users_map)
            
            print("\n" + "="*60)
            print("✅ DATABASE SEEDING COMPLETE!")
            print("="*60)
            
            print(f"\n📊 Summary:")
            print(f"  Churches: {len(churches_map)}")
            print(f"  Users: {len(users_map)}")
            print(f"  Members: {len(members_map)}")
            
            print("\n🚀 Next steps:")
            print("  1. python manage.py runserver")
            print("  2. Visit: http://{subdomain}.localhost:8000/api/docs/")
            print("\n")
    
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

