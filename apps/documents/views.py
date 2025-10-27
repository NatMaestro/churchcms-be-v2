"""
Document views.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Document
from .serializers import DocumentSerializer


class DocumentViewSet(viewsets.ModelViewSet):
    """Document management viewset."""
    
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['category', 'member', 'is_public']
    search_fields = ['file_name']
    ordering_fields = ['created_at', 'file_name']
    
    def get_queryset(self):
        """Filter documents."""
        user = self.request.user
        
        # Admins see all
        if user.is_church_admin or user.is_superadmin:
            return Document.objects.all()
        
        # Members see:
        # 1. Their own documents
        # 2. Public documents
        if hasattr(user, 'member_profile'):
            from django.db.models import Q
            return Document.objects.filter(
                Q(member=user.member_profile) | Q(is_public=True)
            )
        
        return Document.objects.filter(is_public=True)
    
    def perform_create(self, serializer):
        """Set uploaded_by to current user."""
        serializer.save(uploaded_by=self.request.user)
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """
        Upload a document.
        
        POST /api/v1/documents/upload/
        """
        # TODO: Implement file upload with S3/local storage
        return Response({
            'success': False,
            'error': 'File upload not implemented yet'
        }, status=status.HTTP_501_NOT_IMPLEMENTED)
