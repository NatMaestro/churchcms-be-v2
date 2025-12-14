"""
Theme models for church customization.
"""

from django.db import models


class Theme(models.Model):
    """
    Theme customization for churches.
    Each church can have a custom theme.
    """
    
    # Store church_id as integer (avoid cross-schema FK)
    # The actual Church object is in public schema
    church_id = models.BigIntegerField(
        db_index=True,
        help_text="ID of the church this theme belongs to",
        default=0  # Temporary default for migration
    )
    
    # Theme Data (JSON field)
    theme = models.JSONField(default=dict)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'themes'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Theme for church #{self.church_id}"
    
    def get_theme_data(self):
        """Get theme with defaults."""
        default_theme = {
            'id': 'default',
            'name': 'Default',
            'colors': {
                'primary': '#1e293b',
                'secondary': '#64748b',
                'accent': '#0ea5e9',
                'background': '#f8fafc',
                'surface': '#ffffff',
                'text': '#0f172a',
                'textSecondary': '#475569',
                'border': '#cbd5e1',
                'success': '#059669',
                'warning': '#d97706',
                'error': '#dc2626'
            },
            'fonts': {
                'heading': 'Inter, system-ui, sans-serif',
                'body': 'Inter, system-ui, sans-serif'
            },
            'spacing': {
                'borderRadius': '0.5rem',
                'shadow': '0 1px 3px 0 rgb(0 0 0 / 0.1)'
            }
        }
        
        # Merge with custom theme
        if self.theme:
            return {**default_theme, **self.theme}
        
        return default_theme
