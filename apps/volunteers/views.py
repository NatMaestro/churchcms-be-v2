"""
Volunteer views.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from .models import VolunteerOpportunity, VolunteerSignup, VolunteerHours
from .serializers import (
    VolunteerOpportunitySerializer,
    VolunteerSignupSerializer,
    VolunteerHoursSerializer
)
from core.permissions import IsAdminOrReadOnly


class VolunteerOpportunityViewSet(viewsets.ModelViewSet):
    """Volunteer opportunity management viewset."""
    
    queryset = VolunteerOpportunity.objects.all()
    serializer_class = VolunteerOpportunitySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filterset_fields = ['category', 'is_active', 'is_urgent', 'schedule']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'start_date', 'title']
    
    def get_queryset(self):
        """Filter opportunities by active status."""
        return VolunteerOpportunity.objects.filter(is_active=True).order_by('-created_at')
    
    def perform_create(self, serializer):
        """Set created_by to current user."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def signup(self, request, pk=None):
        """
        Sign up for volunteer opportunity.
        
        POST /api/v1/volunteer-opportunities/:id/signup/
        Body: { "member_id": "xxx", "notes": "..." }
        """
        opportunity = self.get_object()
        
        # Check if full
        if opportunity.is_full:
            return Response({
                'success': False,
                'error': 'Opportunity is full'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        member_id = request.data.get('member_id')
        notes = request.data.get('notes', '')
        
        # Create signup
        signup, created = VolunteerSignup.objects.get_or_create(
            opportunity=opportunity,
            member_id=member_id,
            defaults={
                'user': request.user,
                'notes': notes,
                'status': 'pending'
            }
        )
        
        if not created:
            return Response({
                'success': False,
                'error': 'Already signed up for this opportunity'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update spots filled
        opportunity.spots_filled += 1
        opportunity.save()
        
        return Response({
            'success': True,
            'message': 'Signed up successfully',
            'signup': VolunteerSignupSerializer(signup).data
        })
    
    @action(detail=True, methods=['delete'])
    def withdraw(self, request, pk=None):
        """
        Withdraw from volunteer opportunity.
        
        DELETE /api/v1/volunteer-opportunities/:id/withdraw/
        Body: { "member_id": "xxx" }
        """
        opportunity = self.get_object()
        member_id = request.data.get('member_id')
        
        try:
            signup = VolunteerSignup.objects.get(
                opportunity=opportunity,
                member_id=member_id
            )
            signup.status = 'cancelled'
            signup.save()
            
            # Update spots filled
            if opportunity.spots_filled > 0:
                opportunity.spots_filled -= 1
                opportunity.save()
            
            return Response({
                'success': True,
                'message': 'Withdrawn successfully'
            })
        except VolunteerSignup.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Not signed up for this opportunity'
            }, status=status.HTTP_404_NOT_FOUND)


class VolunteerSignupViewSet(viewsets.ModelViewSet):
    """Volunteer signup management viewset."""
    
    queryset = VolunteerSignup.objects.all()
    serializer_class = VolunteerSignupSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'opportunity']
    ordering_fields = ['signup_date', 'status']
    
    def get_queryset(self):
        """Filter signups."""
        user = self.request.user
        if user.is_church_admin or user.is_superadmin:
            return VolunteerSignup.objects.all()
        # Members see only their signups
        return VolunteerSignup.objects.filter(user=user)


class VolunteerHoursViewSet(viewsets.ModelViewSet):
    """Volunteer hours management viewset."""
    
    queryset = VolunteerHours.objects.all()
    serializer_class = VolunteerHoursSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['member', 'opportunity', 'date']
    ordering_fields = ['date', 'hours']
    
    def get_queryset(self):
        """Filter hours."""
        user = self.request.user
        if user.is_church_admin or user.is_superadmin:
            return VolunteerHours.objects.all()
        # Members see only their hours
        if hasattr(user, 'member_profile'):
            return VolunteerHours.objects.filter(member=user.member_profile)
        return VolunteerHours.objects.none()
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get volunteer hours summary for current user.
        
        GET /api/v1/volunteer-hours/summary/
        """
        if not hasattr(request.user, 'member_profile'):
            return Response({
                'success': True,
                'summary': {'total_hours': 0, 'opportunities_count': 0}
            })
        
        hours = VolunteerHours.objects.filter(member=request.user.member_profile)
        
        summary = {
            'total_hours': hours.aggregate(total=Sum('hours'))['total'] or 0,
            'opportunities_count': hours.values('opportunity').distinct().count(),
            'verified_hours': hours.filter(verified_by__isnull=False).aggregate(
                total=Sum('hours')
            )['total'] or 0,
        }
        
        return Response({
            'success': True,
            'summary': summary
        })
