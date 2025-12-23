"""
Management command to toggle subscription bypass for churches.
Usage:
    python manage.py toggle_subscription_bypass <subdomain> --enable
    python manage.py toggle_subscription_bypass <subdomain> --disable
    python manage.py toggle_subscription_bypass <subdomain>  # Check status
"""
from django.core.management.base import BaseCommand
from apps.churches.models import Church


class Command(BaseCommand):
    help = 'Toggle subscription bypass for a church by subdomain'

    def add_arguments(self, parser):
        parser.add_argument('subdomain', type=str, help='Church subdomain')
        parser.add_argument('--enable', action='store_true', help='Enable subscription bypass')
        parser.add_argument('--disable', action='store_true', help='Disable subscription bypass')
        parser.add_argument('--list-all', action='store_true', help='List all churches with bypass enabled')

    def handle(self, *args, **options):
        if options['list_all']:
            # List all churches with bypass enabled
            churches = Church.objects.filter(bypass_subscription_check=True)
            if churches.exists():
                self.stdout.write(self.style.SUCCESS(f'\nFound {churches.count()} church(es) with bypass enabled:\n'))
                for church in churches:
                    self.stdout.write(f'  - {church.name} ({church.subdomain}) - ID: {church.id}')
            else:
                self.stdout.write(self.style.WARNING('\nNo churches have bypass enabled.\n'))
            return

        try:
            church = Church.objects.get(subdomain=options['subdomain'])
            
            if options['enable']:
                if church.bypass_subscription_check:
                    self.stdout.write(self.style.WARNING(f'Bypass already ENABLED for {church.name}'))
                else:
                    church.bypass_subscription_check = True
                    church.save()
                    self.stdout.write(self.style.SUCCESS(f'✅ Subscription bypass ENABLED for: {church.name}'))
                    self.stdout.write(f'   Subdomain: {church.subdomain}')
                    self.stdout.write(f'   ID: {church.id}')
                    
            elif options['disable']:
                if not church.bypass_subscription_check:
                    self.stdout.write(self.style.WARNING(f'Bypass already DISABLED for {church.name}'))
                else:
                    church.bypass_subscription_check = False
                    church.save()
                    self.stdout.write(self.style.SUCCESS(f'✅ Subscription bypass DISABLED for: {church.name}'))
                    self.stdout.write(f'   Subdomain: {church.subdomain}')
                    self.stdout.write(f'   ID: {church.id}')
                    self.stdout.write(self.style.WARNING('   ⚠️  Subscription checks are now active!'))
            else:
                # Just show status
                status = 'ENABLED ✅' if church.bypass_subscription_check else 'DISABLED ❌'
                self.stdout.write(f'\nChurch: {church.name}')
                self.stdout.write(f'Subdomain: {church.subdomain}')
                self.stdout.write(f'Subscription Bypass: {status}')
                self.stdout.write(f'Plan: {church.plan}')
                self.stdout.write(f'Subscription Status: {church.subscription_status}')
                
        except Church.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ Church with subdomain "{options["subdomain"]}" not found')
            )
            self.stdout.write('\nAvailable churches:')
            for church in Church.objects.all()[:10]:  # Show first 10
                self.stdout.write(f'  - {church.subdomain} ({church.name})')
            if Church.objects.count() > 10:
                self.stdout.write(f'  ... and {Church.objects.count() - 10} more')


