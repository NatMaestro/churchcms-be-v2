"""
Theme views.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Theme
from .serializers import ThemeSerializer


class ThemeViewSet(viewsets.ModelViewSet):
    """Theme management viewset."""
    
    queryset = Theme.objects.all()
    serializer_class = ThemeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter themes by church."""
        user = self.request.user
        if user.is_superadmin:
            return Theme.objects.all()
        elif user.church_id:
            return Theme.objects.filter(church_id=user.church_id)
        return Theme.objects.none()
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """
        Get current church's theme.
        
        GET /api/v1/themes/current/
        """
        if not request.user.church_id:
            return Response({
                'success': False,
                'error': 'No church associated with user'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            theme = Theme.objects.get(church_id=request.user.church_id, is_active=True)
            serializer = ThemeSerializer(theme)
            return Response({
                'success': True,
                'theme': serializer.data
            })
        except Theme.DoesNotExist:
            # Return default theme
            return Response({
                'success': True,
                'theme': {
                    'id': 'default',
                    'church_id': request.user.church_id,
                    'theme': {},
                    'theme_data': Theme().get_theme_data()
                }
            })
    
    @action(detail=False, methods=['post', 'put'])
    def save(self, request):
        """
        Save or update church theme.
        
        POST/PUT /api/v1/themes/save/
        Body: { "theme": {...} }
        """
        if not request.user.church_id:
            return Response({
                'success': False,
                'error': 'No church associated with user'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        theme_data = request.data.get('theme', {})
        
        # Get or create theme
        theme, created = Theme.objects.get_or_create(
            church_id=request.user.church_id,
            defaults={'theme': theme_data, 'is_active': True}
        )
        
        if not created:
            # Update existing theme
            theme.theme = theme_data
            theme.save()
        
        serializer = ThemeSerializer(theme)
        
        return Response({
            'success': True,
            'message': 'Theme saved successfully',
            'theme': serializer.data
        })
