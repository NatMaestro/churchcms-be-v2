"""
Theme serializers.
"""

from rest_framework import serializers
from .models import Theme


class ThemeSerializer(serializers.ModelSerializer):
    """Theme serializer."""
    
    church_name = serializers.CharField(source='church.name', read_only=True)
    theme_data = serializers.SerializerMethodField()
    
    class Meta:
        model = Theme
        fields = ['id', 'church', 'church_name', 'theme', 'theme_data', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_theme_data(self, obj):
        """Get complete theme with defaults."""
        return obj.get_theme_data()

