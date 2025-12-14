"""
Django admin for Prayers app
"""
from django.contrib import admin
from .models import PrayerRequest


@admin.register(PrayerRequest)
class PrayerRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'member', 'category', 'urgency', 'status', 'created_at']
    list_filter = ['status', 'category', 'urgency', 'is_public', 'is_confidential', 'created_at']
    search_fields = ['title', 'description', 'member__first_name', 'member__last_name', 'requester_name']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['member', 'assigned_to']
