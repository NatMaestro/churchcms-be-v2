"""
Django admin for Payments app
"""
from django.contrib import admin
from .models import Payment, Pledge, TaxReceipt


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['reference', 'member', 'amount', 'type', 'method', 'date', 'status']
    list_filter = ['type', 'method', 'status', 'date']
    search_fields = ['reference', 'member__first_name', 'member__last_name']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['member']


@admin.register(Pledge)
class PledgeAdmin(admin.ModelAdmin):
    list_display = ['member', 'amount', 'frequency', 'start_date', 'end_date', 'status']
    list_filter = ['frequency', 'status', 'start_date']
    search_fields = ['member__first_name', 'member__last_name']
    raw_id_fields = ['member']


@admin.register(TaxReceipt)
class TaxReceiptAdmin(admin.ModelAdmin):
    list_display = ['member', 'fiscal_year', 'total_amount', 'receipt_number', 'generated_at']
    list_filter = ['fiscal_year', 'generated_at']
    search_fields = ['member__first_name', 'member__last_name', 'receipt_number']
    raw_id_fields = ['member']
