"""
Django admin for Churches app
"""
from django.contrib import admin
from .models import Church, Domain
from .models_subscription_payment import SubscriptionPayment


@admin.register(Church)
class ChurchAdmin(admin.ModelAdmin):
    list_display = ['name', 'subdomain', 'schema_name', 'email', 'plan', 'is_active', 'created_at']
    list_filter = ['plan', 'is_active', 'denomination']
    search_fields = ['name', 'subdomain', 'email']
    readonly_fields = ['schema_name', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'subdomain', 'schema_name', 'email', 'phone', 'address', 'denomination')
        }),
        ('Configuration', {
            'fields': ('plan', 'is_active', 'website')
        }),
        ('Settings', {
            'fields': ('branding_settings', 'payment_settings', 'member_settings', 'features'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['domain', 'tenant', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['domain', 'tenant__name']
    raw_id_fields = ['tenant']


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = ['church', 'plan', 'amount', 'currency', 'status', 'subscription_activated', 'created_at']
    list_filter = ['status', 'plan', 'duration', 'subscription_activated', 'created_at']
    search_fields = ['church__name', 'reference', 'paystack_reference', 'user_email']
    readonly_fields = ['reference', 'paystack_reference', 'paystack_response', 'created_at', 'updated_at', 'completed_at']
    raw_id_fields = ['church']
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('church', 'plan', 'duration', 'amount', 'currency', 'status')
        }),
        ('Paystack Details', {
            'fields': ('reference', 'paystack_reference', 'authorization_url', 'paystack_response')
        }),
        ('Subscription Activation', {
            'fields': ('subscription_activated', 'subscription_start_date', 'subscription_end_date')
        }),
        ('User Information', {
            'fields': ('user_email', 'user_name')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
