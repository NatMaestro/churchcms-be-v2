"""
Seed ONE church at a time from db.json
More reliable than seeding all at once
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
from apps.events.models import Event
from apps.payments.models import Payment
from apps.ministries.models import Ministry
from apps.announcements.models import Announcement
from apps.themes.models import Theme
from django.db import connection

# Path to db.json
DB_JSON_PATH = Path(__file__).parent.parent / 'faithflow-studio' / 'db.json'


def parse_datetime(date_string):
    """Parse datetime string"""
    if not date_string:
        return timezone.now()
    try:
        dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
    except:
        return timezone.now()


def seed_church(church_data, users_data, members_data, themes_data):
    """Seed a single church with all its data"""
    subdomain = church_data.get('subdomain', 'church')
    
    print(f"\n{'='*60}")
    print(f"🏢 Seeding: {church_data.get('name')}")
    print(f"{'='*60}\n")
    
    # 1. Create church
    print("1️⃣ Creating church...")
    church, created = Church.objects.get_or_create(
        subdomain=subdomain,
        defaults={
            'schema_name': subdomain,
            'name': church_data.get('name', 'Unknown Church'),
            'email': church_data.get('email', ''),
            'phone': church_data.get('phone', ''),
            'address': church_data.get('address', ''),
            'denomination': church_data.get('denomination', ''),
            'website': church_data.get('website', ''),
            'plan': church_data.get('plan', 'trial'),
            'is_active': church_data.get('isActive', True),
            'branding_settings': church_data.get('brandingSettings', {}),
            'payment_settings': church_data.get('paymentSettings', {}),
            'member_settings': church_data.get('memberSettings', {}),
            'features': church_data.get('features', {}),
        }
    )
    
    action = "✅ Created" if created else "ℹ️  Already exists"
    print(f"   {action}: {church.name}")
    
    # 2. Create domain
    print("\n2️⃣ Creating domain...")
    domain_name = f"{subdomain}.localhost"
    domain, _ = Domain.objects.get_or_create(
        domain=domain_name,
        defaults={'tenant': church, 'is_primary': True}
    )
    print(f"   ✅ Domain: {domain_name}")
    
    # 3. Switch to tenant schema
    connection.set_tenant(church)
    print(f"\n3️⃣ Switched to {subdomain} schema")
    
    # 4. Create users for this church
    print("\n4️⃣ Creating users...")
    church_users = [u for u in users_data if u.get('churchId') == church_data.get('id')]
    user_count = 0
    for user_data in church_users:
        try:
            user, created = User.objects.get_or_create(
                email=user_data.get('email'),
                defaults={
                    'name': user_data.get('name', ''),
                    'church': church,
                    'role': user_data.get('role', 'member'),
                    'is_active': user_data.get('isActive', True),
                }
            )
            if created:
                user.set_password(user_data.get('password', 'password123'))
                user.save()
                user_count += 1
                print(f"   ✅ {user.name} ({user.email})")
        except Exception as e:
            print(f"   ⚠️  Skipped user {user_data.get('email')}: {e}")
    
    print(f"   📊 Total users: {user_count}")
    
    # 5. Create themes
    print("\n5️⃣ Creating themes...")
    church_themes = [t for t in themes_data if t.get('churchId') == church_data.get('id')]
    theme_count = 0
    for theme_data in church_themes:
        try:
            theme_info = theme_data.get('theme', {})
            theme, created = Theme.objects.get_or_create(
                church=church,
                defaults={'theme': theme_info, 'is_active': True}
            )
            if created:
                theme_count += 1
                print(f"   ✅ {theme_info.get('name', 'Theme')}")
        except Exception as e:
            print(f"   ⚠️  Theme error: {e}")
    
    print(f"   📊 Total themes: {theme_count}")
    
    # 6. Create members
    print("\n6️⃣ Creating members...")
    church_members = [m for m in members_data if m.get('churchId') == church_data.get('id')]
    member_count = 0
    for member_data in church_members[:10]:  # Limit to first 10 for testing
        try:
            member, created = Member.objects.get_or_create(
                member_id=member_data.get('memberId', member_data.get('id')),
                defaults={
                    'first_name': member_data.get('firstName', ''),
                    'last_name': member_data.get('lastName', ''),
                    'email': member_data.get('email', ''),
                    'phone': member_data.get('phone', ''),
                    'date_of_birth': member_data.get('dateOfBirth'),
                    'gender': member_data.get('gender', 'Other'),
                    'address': member_data.get('address', ''),
                    'status': member_data.get('status', 'active'),
                }
            )
            if created:
                member_count += 1
        except Exception as e:
            print(f"   ⚠️  Member error: {e}")
    
    print(f"   ✅ Created {member_count} members")
    
    print(f"\n{'='*60}")
    print(f"✅ {church.name} seeded successfully!")
    print(f"{'='*60}\n")
    
    return church


def main():
    """Main seeding function"""
    print("\n" + "="*60)
    print("🌱 FAITHFLOW - SEED ONE CHURCH")
    print("="*60 + "\n")
    
    # Load data
    print(f"📂 Loading data from: {DB_JSON_PATH}\n")
    
    if not DB_JSON_PATH.exists():
        print(f"❌ Error: db.json not found at {DB_JSON_PATH}")
        return
    
    with open(DB_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    churches = data.get('churches', [])
    users = data.get('users', [])
    members = data.get('members', [])
    themes = data.get('themes', [])
    
    print(f"Found {len(churches)} churches in db.json\n")
    
    # List churches
    for i, church in enumerate(churches, 1):
        print(f"{i}. {church.get('name')} ({church.get('subdomain')})")
    
    print(f"\n{len(churches) + 1}. Seed ALL churches")
    print(f"{len(churches) + 2}. Exit")
    
    # Get choice
    try:
        choice = int(input(f"\nSelect church to seed (1-{len(churches) + 2}): "))
        
        if choice == len(churches) + 2:
            print("❌ Cancelled")
            return
        elif choice == len(churches) + 1:
            # Seed all
            print("\n🚀 Seeding ALL churches...\n")
            for church_data in churches:
                try:
                    seed_church(church_data, users, members, themes)
                except Exception as e:
                    print(f"❌ Error seeding {church_data.get('name')}: {e}\n")
        elif 1 <= choice <= len(churches):
            # Seed selected church
            church_data = churches[choice - 1]
            seed_church(church_data, users, members, themes)
        else:
            print("❌ Invalid choice")
    except (ValueError, KeyboardInterrupt):
        print("\n❌ Cancelled")


if __name__ == '__main__':
    main()

