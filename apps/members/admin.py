"""
Django admin for Members app
"""
from django.contrib import admin
from .models import Member, MemberWorkflow, MemberRequest


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['member_id', 'first_name', 'last_name', 'email', 'phone', 'status', 'created_at']
    list_filter = ['status', 'gender', 'created_at']
    search_fields = ['member_id', 'first_name', 'last_name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('member_id', 'first_name', 'last_name', 'surname', 'other_names')
        }),
        ('Contact', {
            'fields': ('email', 'phone', 'telephone_home', 'address', 'postal_address')
        }),
        ('Personal', {
            'fields': ('gender', 'date_of_birth', 'place_of_birth', 'nationality')
        }),
        ('Status', {
            'fields': ('status', 'membership_date')
        }),
        ('Additional Data', {
            'fields': ('sacraments', 'denomination_specific_data', 'notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MemberWorkflow)
class MemberWorkflowAdmin(admin.ModelAdmin):
    list_display = ['member', 'type', 'status', 'assigned_to', 'created_at']
    list_filter = ['type', 'status', 'created_at']
    search_fields = ['member__first_name', 'member__last_name']
    raw_id_fields = ['member', 'assigned_to']


@admin.register(MemberRequest)
class MemberRequestAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'status', 'reviewed_by', 'submitted_at']
    list_filter = ['status', 'gender', 'marital_status', 'submitted_at']
    search_fields = ['name', 'email', 'phone']
    raw_id_fields = ['reviewed_by']
    readonly_fields = ['submitted_at']
