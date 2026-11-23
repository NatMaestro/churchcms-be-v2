"""
Dues API.

Church staff set up plans and categories, assign members, record and
reverse dues payments, and see every card and the arrears list. A member
sees only their own dues card (GET /dues/my-card/) and nothing else.
"""
import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from apps.members.models import Member
from core.member_context import is_church_staff, member_for

from . import services
from .models import DuesAssignment, DuesCategory, DuesPayment, DuesPlan
from .serializers import (
    DuesAssignmentSerializer,
    DuesCategorySerializer,
    DuesPaymentSerializer,
    DuesPlanSerializer,
    RecordDuesPaymentSerializer,
)

from apps.churches.module_access import requires_module

# Every endpoint here refuses while the church has this module switched off.
MODULE = requires_module('dues')

logger = logging.getLogger(__name__)


class IsChurchStaff(permissions.BasePermission):
    message = 'Dues are managed by church staff.'

    def has_permission(self, request, view):
        return is_church_staff(request.user)


class DuesPlanViewSet(viewsets.ModelViewSet):
    queryset = DuesPlan.objects.prefetch_related('categories')
    serializer_class = DuesPlanSerializer
    permission_classes = [permissions.IsAuthenticated, IsChurchStaff, MODULE]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']  # plans are paused, never deleted

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def cards(self, request, pk=None):
        """GET /dues/plans/:id/cards/  every active member's card for this plan."""
        return Response(services.all_cards(self.get_object()))

    @action(detail=True, methods=['get'])
    def arrears(self, request, pk=None):
        """GET /dues/plans/:id/arrears/  members who are behind, most owed first."""
        behind = [card for card in services.all_cards(self.get_object()) if card['arrears'] > 0]
        behind.sort(key=lambda card: card['arrears'], reverse=True)
        return Response(behind)


class DuesCategoryViewSet(viewsets.ModelViewSet):
    queryset = DuesCategory.objects.all()
    serializer_class = DuesCategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsChurchStaff, MODULE]
    filterset_fields = ['plan']

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        if DuesPayment.objects.filter(plan=category.plan, status=DuesPayment.COMPLETED).exists():
            return Response({'success': False,
                             'error': 'This plan already has payments; rename the category instead of deleting it.'},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)


class DuesAssignmentViewSet(viewsets.ModelViewSet):
    queryset = DuesAssignment.objects.select_related('member', 'category')
    serializer_class = DuesAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsChurchStaff, MODULE]
    filterset_fields = ['plan', 'member']


class DuesPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """Recorded dues payments: staff list them, record new ones and reverse mistakes."""

    queryset = DuesPayment.objects.select_related('member', 'plan')
    serializer_class = DuesPaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsChurchStaff, MODULE]
    filterset_fields = ['plan', 'member', 'status']

    def create(self, request):
        serializer = RecordDuesPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        plan = get_object_or_404(DuesPlan, pk=data['plan'])
        member = get_object_or_404(Member, pk=data['member'])
        try:
            payment = services.record_payment(
                plan=plan, member=member, amount=data['amount'], months=data['months'],
                payment_date=data['date'], method=data['method'], reference=data.get('reference', ''),
                notes=data.get('notes', ''), recorded_by=request.user,
            )
        except services.DuesError as error:
            return Response({'success': False, 'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        logger.info('dues_payment_recorded', extra={'payment_id': payment.pk, 'actor_id': request.user.pk})
        return Response(DuesPaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        """POST /dues/payments/:id/reverse/  { "reason": "..." }"""
        try:
            payment = services.reverse_payment(self.get_object(), request.data.get('reason'), request.user)
        except services.DuesError as error:
            return Response({'success': False, 'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        logger.info('dues_payment_reversed', extra={'payment_id': payment.pk, 'actor_id': request.user.pk})
        return Response(DuesPaymentSerializer(payment).data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, MODULE])
def member_card(request):
    """
    GET /dues/member-card/?plan=<id>&member=<id>  (staff)  one member's card.
    GET /dues/my-card/?plan=<id>                  (anyone) the signed-in member's own card;
    without a plan, the newest active plan.
    """
    own = request.path.rstrip('/').endswith('my-card')
    if own:
        member = member_for(request.user)
        if member is None:
            return Response({'success': False, 'error': 'No member record is linked to this account.'},
                            status=status.HTTP_404_NOT_FOUND)
    else:
        if not is_church_staff(request.user):
            return Response({'success': False, 'error': 'Dues are managed by church staff.'},
                            status=status.HTTP_403_FORBIDDEN)
        member = get_object_or_404(Member, pk=request.query_params.get('member'))

    plans = DuesPlan.objects.filter(is_active=True)
    plan_id = request.query_params.get('plan')
    plan = get_object_or_404(plans, pk=plan_id) if plan_id else plans.order_by('-year', '-created_at').first()
    if plan is None:
        return Response({'plan': None, 'plans': []})
    card = services.load_card(member, plan)
    card['plans'] = [{'id': p.pk, 'name': p.name, 'year': p.year} for p in plans.order_by('-year')]
    card['today'] = timezone.localdate()
    return Response(card)
