"""
Theme models for church customization.
"""

from django.db import models


class Theme(models.Model):
    """
    Theme customization for churches.
    Each church can have a custom theme.
    """
    
    church = models.ForeignKey(
        'churches.Church',
        on_delete=models.CASCADE,
        related_name='themes'
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
        return f"Theme for {self.church.name}"
    
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
