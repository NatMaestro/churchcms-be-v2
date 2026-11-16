"""
Serializers for the platform admin API (platform superadmins only).
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.churches.models import Church
from apps.churches.models_plan import Plan
from apps.churches.models_subscription_payment import SubscriptionPayment
from apps.churches.subscriptions import MANUAL_PAYMENT_METHODS, MAX_TRIAL_EXTENSION_DAYS, account_state

from .models import WHATSAPP_NUMBER_VALIDATOR, DemoRequest, PlatformSettings

MAX_PLAN_FEATURES = 20
MAX_FEATURE_LENGTH = 120


class PlatformPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ['id', 'code', 'name', 'tagline', 'price_monthly', 'price_yearly', 'member_limit',
                  'features', 'is_active', 'is_public', 'is_featured', 'sort_order',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_code(self, value):
        # Churches and payments store the code, so it can never change once created.
        if self.instance is not None and value != self.instance.code:
            raise serializers.ValidationError('A plan code cannot be changed once created.')
        if value == 'trial':
            raise serializers.ValidationError('"trial" is reserved.')
        return value

    def validate_price_monthly(self, value):
        if value <= 0:
            raise serializers.ValidationError('Monthly price must be more than 0.')
        return value

    def validate_price_yearly(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError('Yearly price must be more than 0, or left empty.')
        return value

    def validate_features(self, value):
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise serializers.ValidationError('Features must be a list of short lines of text.')
        if len(value) > MAX_PLAN_FEATURES:
            raise serializers.ValidationError(f'At most {MAX_PLAN_FEATURES} features.')
        if any(len(item) > MAX_FEATURE_LENGTH for item in value):
            raise serializers.ValidationError(f'Each feature must be at most {MAX_FEATURE_LENGTH} characters.')
        return [item.strip() for item in value if item.strip()]


class PlatformPaymentSerializer(serializers.ModelSerializer):
    church_name = serializers.CharField(source='church.name', read_only=True)
    church_subdomain = serializers.CharField(source='church.subdomain', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.name', read_only=True, default=None)

    class Meta:
        model = SubscriptionPayment
        fields = ['id', 'church', 'church_name', 'church_subdomain', 'amount', 'currency', 'plan',
                  'duration', 'payment_method', 'reference', 'status', 'subscription_activated',
                  'subscription_start_date', 'subscription_end_date', 'recorded_by_name', 'note',
                  'created_at', 'completed_at']


class PlatformChurchSerializer(serializers.ModelSerializer):
    account_state = serializers.SerializerMethodField()
    user_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Church
        fields = ['id', 'name', 'subdomain', 'email', 'phone', 'denomination', 'plan',
                  'subscription_status', 'bypass_subscription_check', 'trial_started_at',
                  'trial_end_date', 'subscription_start_date', 'subscription_end_date',
                  'account_state', 'user_count', 'created_at']

    def get_account_state(self, church):
        return account_state(church)


class RecordPaymentSerializer(serializers.Serializer):
    plan = serializers.SlugField(max_length=20)
    duration = serializers.ChoiceField(choices=['monthly', 'yearly'])
    method = serializers.ChoiceField(choices=list(MANUAL_PAYMENT_METHODS))
    reference = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=0)
    note = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class ExtendTrialSerializer(serializers.Serializer):
    days = serializers.IntegerField(min_value=1, max_value=MAX_TRIAL_EXTENSION_DAYS)


class SetFlagSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()


class PlatformDemoRequestSerializer(serializers.ModelSerializer):
    church_subdomain = serializers.CharField(source='church.subdomain', read_only=True, default=None)

    class Meta:
        model = DemoRequest
        fields = ['id', 'name', 'role', 'phone', 'email', 'church_name', 'congregation_size',
                  'preferred_time', 'message', 'status', 'notes', 'church', 'church_subdomain',
                  'created_at', 'updated_at']
        # What the person typed is kept as typed; admins change only the follow-up fields.
        read_only_fields = ['id', 'name', 'role', 'phone', 'email', 'church_name', 'congregation_size',
                            'preferred_time', 'message', 'created_at', 'updated_at']


class CreateChurchSerializer(serializers.Serializer):
    church_name = serializers.CharField(max_length=255)
    subdomain = serializers.CharField(max_length=63)
    denomination = serializers.CharField(max_length=100, required=False, allow_blank=True)
    admin_name = serializers.CharField(max_length=255)
    admin_email = serializers.EmailField()
    demo_request = serializers.PrimaryKeyRelatedField(queryset=DemoRequest.objects.all(), required=False,
                                                      allow_null=True)


class PlatformSettingsSerializer(serializers.ModelSerializer):
    # Declared here (not from the model) so pasted forms like "+233 20 123 4567"
    # are cleaned to digits before the format check below.
    whatsapp_number = serializers.CharField(max_length=30, allow_blank=True, required=False)
    updated_by_name = serializers.CharField(source='updated_by.name', read_only=True, default=None)

    class Meta:
        model = PlatformSettings
        fields = ['whatsapp_number', 'contact_email', 'updated_at', 'updated_by_name']
        read_only_fields = ['updated_at', 'updated_by_name']

    def validate_whatsapp_number(self, value):
        # Accept what people paste ("+233 20 123 4567") and store digits only.
        digits = ''.join(character for character in value if character.isdigit())
        if digits:
            try:
                WHATSAPP_NUMBER_VALIDATOR(digits)
            except DjangoValidationError as error:
                raise serializers.ValidationError(error.messages)
        elif value.strip():
            raise serializers.ValidationError('Use the international format with digits only, e.g. 233201234567.')
        return digits
