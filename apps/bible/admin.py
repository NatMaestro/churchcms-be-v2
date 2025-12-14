"""
Django admin for Bible app
"""
from django.contrib import admin
from .models import BibleVerse, ReadingPlan, ReadingProgress


@admin.register(BibleVerse)
class BibleVerseAdmin(admin.ModelAdmin):
    list_display = ['book', 'chapter', 'verse', 'version']
    list_filter = ['book', 'version']
    search_fields = ['book', 'text']


@admin.register(ReadingPlan)
class ReadingPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'duration_days', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ReadingProgress)
class ReadingProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'current_day', 'is_completed', 'started_at']
    list_filter = ['is_completed', 'started_at']
    search_fields = ['user__name', 'plan__name']
    readonly_fields = ['started_at', 'completed_at']
    raw_id_fields = ['user', 'plan']






