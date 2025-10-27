"""
Announcements app configuration.
"""

from django.apps import AppConfig


class AnnouncementsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.announcements'
    label = 'announcements'
    
    def ready(self):
        """Import signals when app is ready."""
        import core.signals
