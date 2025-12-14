"""
Django admin for Communications app
"""
from django.contrib import admin
from .models import Message, Announcement, SMSLog, EmailLog


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'status', 'scheduled_for', 'sent_at']
    list_filter = ['type', 'status', 'scheduled_for']
    search_fields = ['title', 'content']
    readonly_fields = ['sent_at', 'created_at', 'updated_at']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'is_active', 'start_date', 'end_date']
    list_filter = ['type', 'is_active', 'start_date']
    search_fields = ['title', 'content']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ['phone', 'status', 'provider', 'created_at']
    list_filter = ['status', 'provider', 'created_at']
    search_fields = ['phone', 'message']
    readonly_fields = ['created_at']


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['to_email', 'subject', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['to_email', 'subject']
    readonly_fields = ['created_at']






