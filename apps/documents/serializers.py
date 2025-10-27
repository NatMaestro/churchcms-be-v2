"""
Document serializers.
"""

from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    """Document serializer."""
    
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.name', read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'member', 'member_name', 'file_name', 'file_path', 'file_size',
            'file_size_mb', 'mime_type', 'category', 'is_public', 'uploaded_by',
            'uploaded_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'uploaded_by']
    
    def get_file_size_mb(self, obj):
        """Get file size in MB."""
        return round(obj.file_size / (1024 * 1024), 2)

