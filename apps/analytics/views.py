"""
Analytics and dashboard views.
"""

from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta


class DashboardView(APIView):
    """
    Dashboard statistics and overview.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Get dashboard stats.
        
        GET /api/v1/dashboard/stats/
        """
        from apps.members.models import Member
        from apps.events.models import Event
        from apps.payments.models import Payment
        from apps.ministries.models import Ministry
        
        # Member stats
        members = Member.objects.all()
        member_stats = {
            'total': members.count(),
            'active': members.filter(status='active').count(),
            'new_this_month': members.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count()
        }
        
        # Event stats
        events = Event.objects.all()
        upcoming_events = events.filter(date__gte=timezone.now())
        
        event_stats = {
            'total': events.count(),
            'upcoming': upcoming_events.count(),
            'this_month': events.filter(
                date__month=timezone.now().month,
                date__year=timezone.now().year
            ).count()
        }
        
        # Payment stats
        payments = Payment.objects.filter(status='completed')
        this_month_payments = payments.filter(
            date__month=timezone.now().month,
            date__year=timezone.now().year
        )
        
        payment_stats = {
            'total_count': payments.count(),
            'total_amount': payments.aggregate(total=Sum('amount'))['total'] or 0,
            'this_month_amount': this_month_payments.aggregate(total=Sum('amount'))['total'] or 0,
            'this_month_count': this_month_payments.count()
        }
        
        # Ministry stats
        ministry_stats = {
            'total': Ministry.objects.filter(is_active=True).count()
        }
        
        return Response({
            'success': True,
            'stats': {
                'members': member_stats,
                'events': event_stats,
                'payments': payment_stats,
                'ministries': ministry_stats
            }
        })


class AnalyticsView(APIView):
    """
    Advanced analytics and reports.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Get analytics data.
        
        GET /api/v1/analytics/overview/
        """
        # TODO: Implement detailed analytics
        return Response({
            'success': True,
            'message': 'Analytics not fully implemented yet'
        })
