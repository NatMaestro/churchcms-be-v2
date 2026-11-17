"""
Dues serializers.
"""
from decimal import Decimal

from rest_framework import serializers

from .models import PAYMENT_METHODS, DuesAssignment, DuesCategory, DuesPayment, DuesPlan


class DuesCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DuesCategory
        fields = ['id', 'plan', 'name', 'amount', 'min_age', 'max_age', 'sort_order']
        read_only_fields = ['id']

    def validate(self, attrs):
        min_age = attrs.get('min_age', getattr(self.instance, 'min_age', None))
        max_age = attrs.get('max_age', getattr(self.instance, 'max_age', None))
        if min_age is not None and max_age is not None and min_age > max_age:
            raise serializers.ValidationError({'max_age': 'The highest age must not be below the lowest.'})
        return attrs


class DuesPlanSerializer(serializers.ModelSerializer):
    categories = DuesCategorySerializer(many=True, read_only=True)

    class Meta:
        model = DuesPlan
        fields = ['id', 'name', 'year', 'frequency', 'is_active', 'categories', 'created_at', 'updated_at']
        read_only_fields = ['id', 'categories', 'created_at', 'updated_at']

    def validate_frequency(self, value):
        # Once payments exist their meaning depends on the frequency.
        if self.instance and value != self.instance.frequency and self.instance.payments.exists():
            raise serializers.ValidationError('This plan already has payments, so it can no longer change frequency.')
        return value


class DuesAssignmentSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.full_name', read_only=True)

    class Meta:
        model = DuesAssignment
        fields = ['id', 'plan', 'member', 'member_name', 'category', 'is_exempt', 'note', 'updated_at']
        read_only_fields = ['id', 'updated_at']

    def validate(self, attrs):
        plan = attrs.get('plan', getattr(self.instance, 'plan', None))
        category = attrs.get('category', getattr(self.instance, 'category', None))
        if category is not None and plan is not None and category.plan_id != plan.pk:
            raise serializers.ValidationError({'category': 'That category belongs to another plan.'})
        return attrs


class DuesPaymentSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    plan_name = serializers.CharField(source='plan.name', read_only=True)

    class Meta:
        model = DuesPayment
        fields = ['id', 'plan', 'plan_name', 'member', 'member_name', 'amount', 'months', 'date', 'method',
                  'reference', 'status', 'notes', 'created_at']
        read_only_fields = fields


class RecordDuesPaymentSerializer(serializers.Serializer):
    plan = serializers.IntegerField()
    member = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    months = serializers.ListField(child=serializers.IntegerField(min_value=1, max_value=12), required=False,
                                   default=list)
    date = serializers.DateField()
    method = serializers.ChoiceField(choices=PAYMENT_METHODS)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_reference(self, value):
        value = value.strip()
        if value and DuesPayment.objects.filter(reference=value).exists():
            raise serializers.ValidationError('This receipt number is already used.')
        return value
