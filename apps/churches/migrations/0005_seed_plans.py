"""
Seed the plans that used to be hard-coded in the payment view, with the same
prices (GHS), so existing churches and payments keep resolving to a plan.
Platform admins change names, prices and features afterwards; this migration
only creates plans that do not exist yet and never overwrites edits.
"""
from decimal import Decimal

from django.db import migrations

STARTING_PLANS = [
    # code, name, monthly, yearly, sort order, featured
    ('basic', 'Basic', '19.00', '205.00', 10, False),
    ('standard', 'Standard', '29.00', '313.00', 20, True),
    ('premium', 'Premium', '79.00', '853.00', 30, False),
    ('enterprise', 'Enterprise', '199.00', '2149.00', 40, False),
]


def seed_plans(apps, schema_editor):
    Plan = apps.get_model('churches', 'Plan')
    for code, name, monthly, yearly, order, featured in STARTING_PLANS:
        Plan.objects.get_or_create(code=code, defaults={
            'name': name,
            'price_monthly': Decimal(monthly),
            'price_yearly': Decimal(yearly),
            'sort_order': order,
            'is_featured': featured,
        })


def unseed_plans(apps, schema_editor):
    Plan = apps.get_model('churches', 'Plan')
    Plan.objects.filter(code__in=[plan[0] for plan in STARTING_PLANS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('churches', '0004_plans'),
    ]

    operations = [
        migrations.RunPython(seed_plans, unseed_plans),
    ]
