"""
Document models for file management.
"""

from django.db import models
from django.conf import settings


class Document(models.Model):
    """
    Document storage for churches and members.
    """
    
    # Related member (optional)
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True
    )
    
    # File Information
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.IntegerField()  # In bytes
    mime_type = models.CharField(max_length=100)
    
    # Category
    category = models.CharField(
        max_length=50,
        choices=[
            ('certificate', 'Certificate'),
            ('photo', 'Photo'),
            ('document', 'Document'),
            ('receipt', 'Receipt'),
            ('report', 'Report'),
            ('other', 'Other'),
        ],
        default='document'
    )
    
    # Privacy
    is_public = models.BooleanField(default=False)
    
    # Upload tracking
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['member']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.file_name} ({self.category})"
