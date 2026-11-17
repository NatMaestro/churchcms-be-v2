"""
How members give to their church directly: its Mobile Money and bank details,
shown on the member Give page. Set by the church's admin, read by its members.

Stored in Church.payment_settings['giving']. These are the church's public
payment details (what it would print on a notice board); never secret keys.
"""
from django.utils import timezone
from rest_framework import serializers

GIVING_DETAILS_KEY = 'giving'
GIVING_DETAILS_VERSION = 1

MOMO_NETWORKS = [('mtn', 'MTN MoMo'), ('telecel', 'Telecel Cash'), ('airteltigo', 'AirtelTigo Money')]


class GivingDetailsSerializer(serializers.Serializer):
    momo_network = serializers.ChoiceField(choices=MOMO_NETWORKS, required=False, allow_blank=True)
    momo_number = serializers.RegexField(
        r'^0[2-5][0-9]{8}$', required=False, allow_blank=True,
        error_messages={'invalid': 'Use a 10-digit Ghana mobile number, e.g. 0241234567.'})
    momo_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    bank_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    bank_branch = serializers.CharField(max_length=100, required=False, allow_blank=True)
    bank_account_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    bank_account_number = serializers.RegexField(
        r'^[0-9]{6,20}$', required=False, allow_blank=True,
        error_messages={'invalid': 'Use digits only (6 to 20).'})
    instructions = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs.get('momo_number') and not attrs.get('momo_network'):
            raise serializers.ValidationError({'momo_network': 'Choose the Mobile Money network.'})
        if attrs.get('bank_account_number') and not (attrs.get('bank_name') and attrs.get('bank_account_name')):
            raise serializers.ValidationError({'bank_name': 'Add the bank name and account name too.'})
        return attrs


def read_giving_details(church):
    """The church's giving details, with every field present (empty when unset)."""
    stored = (church.payment_settings or {}).get(GIVING_DETAILS_KEY, {})
    details = {name: stored.get(name, '') for name in GivingDetailsSerializer().fields}
    details.update({
        'version': GIVING_DETAILS_VERSION,
        'updated_at': stored.get('updated_at'),
        'updated_by_name': stored.get('updated_by_name', ''),
    })
    return details


def save_giving_details(church, validated, user):
    """Replace the church's giving details (other payment settings are kept)."""
    details = {name: validated.get(name, '') for name in GivingDetailsSerializer().fields}
    details['updated_at'] = timezone.now().isoformat()
    details['updated_by_name'] = getattr(user, 'name', '') or ''
    church.payment_settings = {**(church.payment_settings or {}), GIVING_DETAILS_KEY: details}
    church.save(update_fields=['payment_settings', 'updated_at'])
    return read_giving_details(church)
