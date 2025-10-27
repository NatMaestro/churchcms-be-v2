"""
Events app configuration.
"""

from django.apps import AppConfig


class EventsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.events'
    label = 'events'
    
    def ready(self):
        """Import signals when app is ready."""
        import core.signals  # This will register all signals
