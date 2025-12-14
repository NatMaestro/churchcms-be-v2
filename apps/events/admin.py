"""
Django admin for Events app
"""
from django.contrib import admin
from .models import Event, EventRegistration


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'date', 'location', 'capacity', 'is_recurring']
    list_filter = ['type', 'is_recurring', 'date']
    search_fields = ['title', 'description', 'location']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ['event', 'member', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['event__title', 'member__first_name', 'member__last_name']
    raw_id_fields = ['event', 'member']
