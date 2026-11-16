"""
Demo requests: churches asking to see Flocktend before signing up.

Personal data. What is stored, who sees it and how long it is kept:
- Stored: only the fields below, as typed on the landing page form.
- Seen by: platform superadmins only, through the platform admin API; every
  read and change is logged with the admin's id (never the field values).
- Kept: until it becomes a paying or trial church, or for
  STALE_DEMO_REQUEST_DAYS after the last update for requests that went
  nowhere (see purge_stale_demo_requests). An admin can delete one at any time.

Classification per field: PERSONAL = identifies a person; CHURCH = about the
organisation; INTERNAL = written by platform admins.
"""
from datetime import timedelta

from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

STALE_DEMO_REQUEST_DAYS = 365
OPEN_STATUSES = ('new', 'contacted', 'demo_booked')


class DemoRequest(models.Model):
    CONGREGATION_SIZES = [
        ('under_100', 'Under 100'),
        ('100_300', '100 to 300'),
        ('300_1000', '300 to 1,000'),
        ('over_1000', 'Over 1,000'),
    ]
    STATUSES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('demo_booked', 'Demo booked'),
        ('trial', 'On trial'),
        ('paying', 'Paying'),
        ('lost', 'Lost'),
    ]

    name = models.CharField(max_length=150)                      # PERSONAL
    role = models.CharField(max_length=100, blank=True)          # PERSONAL (e.g. pastor, administrator)
    phone = models.CharField(max_length=30)                      # PERSONAL
    email = models.EmailField()                                  # PERSONAL
    church_name = models.CharField(max_length=255)               # CHURCH
    congregation_size = models.CharField(max_length=20, choices=CONGREGATION_SIZES)  # CHURCH
    preferred_time = models.CharField(max_length=200, blank=True)  # PERSONAL (availability)
    message = models.TextField(blank=True, max_length=1000)      # PERSONAL (free text)

    status = models.CharField(max_length=20, choices=STATUSES, default='new')  # INTERNAL
    notes = models.TextField(blank=True)                         # INTERNAL
    church = models.ForeignKey('churches.Church', null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='demo_requests')     # INTERNAL: church created after the demo

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'demo_requests'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'updated_at'])]

    def __str__(self):
        return f'Demo request #{self.pk}'


def purge_stale_demo_requests(now=None):
    """Delete requests that went nowhere and were not touched for a year. Returns the count."""
    cutoff = (now or timezone.now()) - timedelta(days=STALE_DEMO_REQUEST_DAYS)
    stale = DemoRequest.objects.filter(updated_at__lt=cutoff).exclude(status__in=['trial', 'paying'])
    deleted, _ = stale.delete()
    return deleted


WHATSAPP_NUMBER_VALIDATOR = RegexValidator(
    r'^[1-9][0-9]{7,14}$',
    'Use the international format with digits only, e.g. 233201234567.',
)


class PlatformSettings(models.Model):
    """
    Platform-wide settings a platform superadmin edits, shown on the public
    website and the church Billing page. There is exactly one row (pk=1).
    Business contact details only; nothing here identifies a private person.
    """

    SINGLETON_ID = 1

    whatsapp_number = models.CharField(max_length=15, blank=True, validators=[WHATSAPP_NUMBER_VALIDATOR])
    contact_email = models.EmailField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('authentication.User', null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='+')

    class Meta:
        db_table = 'platform_settings'

    def __str__(self):
        return 'Platform settings'

    @classmethod
    def load(cls):
        settings_row, _ = cls.objects.get_or_create(pk=cls.SINGLETON_ID)
        return settings_row
