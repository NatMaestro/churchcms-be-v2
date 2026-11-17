"""
Volunteer views.

Church staff create and manage opportunities (including inactive ones) and
decide on sign-ups. A member sees active opportunities, signs up and
withdraws as themselves (the member comes from the login, any member_id they
send is ignored), and sees only their own sign-ups and hours.
See core.member_context.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import OuterRef, Subquery, Sum
from django.utils import timezone

from core.member_context import acting_member, is_church_staff, member_for
from .models import VolunteerOpportunity, VolunteerSignup, VolunteerHours
from .serializers import (
    VolunteerOpportunitySerializer,
    VolunteerSignupSerializer,
    VolunteerHoursSerializer
)
from core.permissions import IsAdminOrReadOnly

# Sign-ups that take a spot.
ACTIVE_SIGNUP_STATUSES = ('pending', 'approved')


def _recount_spots(opportunity):
    """spots_filled always matches the sign-ups that hold a spot (call inside the row lock)."""
    opportunity.spots_filled = opportunity.signups.filter(status__in=ACTIVE_SIGNUP_STATUSES).count()
    opportunity.save(update_fields=['spots_filled', 'updated_at'])


class VolunteerOpportunityViewSet(viewsets.ModelViewSet):
    """Volunteer opportunity management viewset."""

    queryset = VolunteerOpportunity.objects.all()
    serializer_class = VolunteerOpportunitySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filterset_fields = ['category', 'is_active', 'is_urgent', 'schedule']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'start_date', 'title']

    def get_permissions(self):
        """Any signed-in church user may sign up or withdraw; changing opportunities stays with staff."""
        if self.action in ('signup', 'withdraw'):
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        """Staff see every opportunity; members see active ones. Each carries the viewer's sign-up status."""
        opportunities = VolunteerOpportunity.objects.all()
        if not is_church_staff(self.request.user):
            opportunities = opportunities.filter(is_active=True)
        mine = VolunteerSignup.objects.filter(opportunity=OuterRef('pk'), member__user=self.request.user)
        return opportunities.annotate(my_signup_status=Subquery(mine.values('status')[:1])).order_by('-created_at')

    def perform_create(self, serializer):
        """Set created_by to current user."""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def signup(self, request, pk=None):
        """
        Sign up for volunteer opportunity (as yourself; staff may name a member_id).

        POST /api/v1/volunteer-opportunities/:id/signup/
        Body: { "notes": "..." }
        """
        opportunity = self.get_object()
        member = acting_member(request)
        if member is None:
            return Response({
                'success': False,
                'error': 'No member record found to sign up with.'
            }, status=status.HTTP_400_BAD_REQUEST)
        notes = request.data.get('notes', '')

        with transaction.atomic():
            # Lock the opportunity so two sign-ups cannot both take the last spot.
            opportunity = VolunteerOpportunity.objects.select_for_update().get(pk=opportunity.pk)
            signup = VolunteerSignup.objects.filter(opportunity=opportunity, member=member).first()
            if signup and signup.status in ACTIVE_SIGNUP_STATUSES + ('completed',):
                return Response({
                    'success': False,
                    'error': 'Already signed up for this opportunity'
                }, status=status.HTTP_400_BAD_REQUEST)

            _recount_spots(opportunity)
            if opportunity.is_full:
                return Response({
                    'success': False,
                    'error': 'Opportunity is full'
                }, status=status.HTTP_400_BAD_REQUEST)

            if signup:  # signing up again after withdrawing or being declined
                signup.status = 'pending'
                signup.notes = notes
                signup.approved_by = None
                signup.approved_at = None
                signup.save()
            else:
                signup = VolunteerSignup.objects.create(
                    opportunity=opportunity, member=member, user=member.user or request.user,
                    notes=notes, status='pending',
                )
            _recount_spots(opportunity)

        return Response({
            'success': True,
            'message': 'Signed up successfully',
            'signup': VolunteerSignupSerializer(signup).data
        })

    @action(detail=True, methods=['post', 'delete'])
    def withdraw(self, request, pk=None):
        """
        Withdraw from volunteer opportunity (as yourself; staff may name a member_id).

        POST or DELETE /api/v1/volunteer-opportunities/:id/withdraw/
        """
        opportunity = self.get_object()
        member = acting_member(request)

        with transaction.atomic():
            opportunity = VolunteerOpportunity.objects.select_for_update().get(pk=opportunity.pk)
            signup = VolunteerSignup.objects.filter(
                opportunity=opportunity, member=member, status__in=ACTIVE_SIGNUP_STATUSES,
            ).first() if member else None
            if signup is None:
                return Response({
                    'success': False,
                    'error': 'Not signed up for this opportunity'
                }, status=status.HTTP_404_NOT_FOUND)
            signup.status = 'cancelled'
            signup.save(update_fields=['status'])
            _recount_spots(opportunity)

        return Response({
            'success': True,
            'message': 'Withdrawn successfully'
        })


class VolunteerSignupViewSet(viewsets.ModelViewSet):
    """
    Volunteer signup management viewset. Staff review every sign-up and set
    its status; members read their own (they sign up and withdraw through the
    opportunity's signup / withdraw actions).
    """

    queryset = VolunteerSignup.objects.all()
    serializer_class = VolunteerSignupSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filterset_fields = ['status', 'opportunity']
    ordering_fields = ['signup_date', 'status']

    def get_queryset(self):
        """Filter signups."""
        signups = VolunteerSignup.objects.select_related('member', 'opportunity')
        if is_church_staff(self.request.user):
            return signups
        # Members see only their signups
        return signups.filter(member__user=self.request.user)

    def perform_update(self, serializer):
        """Record who approved a sign-up and when; keep the opportunity's spot count right."""
        previous_status = serializer.instance.status
        with transaction.atomic():
            signup = serializer.save()
            if signup.status == 'approved' and previous_status != 'approved':
                signup.approved_by = self.request.user
                signup.approved_at = timezone.now()
                signup.save(update_fields=['approved_by', 'approved_at'])
            if signup.status != previous_status:
                opportunity = VolunteerOpportunity.objects.select_for_update().get(pk=signup.opportunity_id)
                _recount_spots(opportunity)


class VolunteerHoursViewSet(viewsets.ModelViewSet):
    """Volunteer hours management viewset."""

    queryset = VolunteerHours.objects.all()
    serializer_class = VolunteerHoursSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filterset_fields = ['member', 'opportunity', 'date']
    ordering_fields = ['date', 'hours']

    def get_queryset(self):
        """Filter hours."""
        if is_church_staff(self.request.user):
            return VolunteerHours.objects.all()
        # Members see only their hours (staff record them)
        return VolunteerHours.objects.filter(member__user=self.request.user)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get volunteer hours summary for current user.

        GET /api/v1/volunteer-hours/summary/
        """
        member = member_for(request.user)
        if member is None:
            return Response({
                'success': True,
                'summary': {'total_hours': 0, 'opportunities_count': 0}
            })

        hours = VolunteerHours.objects.filter(member=member)

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
