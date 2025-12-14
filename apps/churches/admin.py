"""
Django admin for Churches app
"""
from django.contrib import admin
from .models import Church, Domain


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
