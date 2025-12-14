"""
Django admin for Reports app
"""
from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'format', 'status', 'generated_by', 'created_at']
    list_filter = ['type', 'format', 'status', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['generated_at', 'created_at']
    raw_id_fields = ['generated_by']






