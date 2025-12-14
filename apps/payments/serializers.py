"""
Payment serializers.
"""

from rest_framework import serializers
from .models import Payment, Pledge, TaxReceipt


class PaymentSerializer(serializers.ModelSerializer):
    """Payment serializer."""
    
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'member', 'member_name', 'amount', 'currency', 'type', 'method',
            'status', 'reference', 'notes', 'date', 'pledge_id', 'is_recurring',
            'recurring_frequency', 'recurring_end_date', 'fiscal_year', 'receipt_number',
            'is_tax_deductible', 'receipt_issued', 'receipt_issued_at', 'category',
            'subcategory', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentListSerializer(serializers.ModelSerializer):
    """Simplified payment serializer for list views."""
    
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'member_name', 'amount', 'currency', 'type', 'method',
            'status', 'reference', 'date'
        ]


class PledgeSerializer(serializers.ModelSerializer):
    """Pledge serializer."""
    
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    amount_remaining = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Pledge
        fields = [
            'id', 'member', 'member_name', 'amount', 'frequency', 'start_date',
            'end_date', 'status', 'amount_paid', 'amount_remaining', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaxReceiptSerializer(serializers.ModelSerializer):
    """Tax receipt serializer."""
    
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.name', read_only=True)
    
    class Meta:
        model = TaxReceipt
        fields = [
            'id', 'member', 'member_name', 'fiscal_year', 'receipt_number', 'total_amount',
            'payment_ids', 'generated_by', 'generated_by_name', 'generated_at', 'pdf_path',
            'email_sent', 'email_sent_at'
        ]
        read_only_fields = ['id', 'generated_at']






