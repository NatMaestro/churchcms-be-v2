"""
Payment views.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
import logging
import uuid

from django.db import transaction
from django.db.models import Count, Sum
from django.db.models.functions import ExtractMonth
from django.utils import timezone
from decimal import Decimal
from .models import Payment, Pledge, TaxReceipt
from .serializers import (
    PaymentNotesSerializer,
    PaymentSerializer,
    PaymentListSerializer,
    PledgeSerializer,
    TaxReceiptSerializer
)
from core.member_context import is_church_staff
from core.permissions import IsAdminOrReadOnly
from core.services import ExportService


logger = logging.getLogger(__name__)
NEWLINE = chr(10)


def _new_reference():
    """A unique reference for a gift recorded without one, e.g. GIFT-3F9A1C2B7D4E."""
    return f'GIFT-{uuid.uuid4().hex[:12].upper()}'


class PaymentViewSet(viewsets.ModelViewSet):
    """
    Payment (gift) management viewset.

    Church staff record gifts and can only add notes afterwards; a mistake is
    corrected by reversing the gift (status "refunded", with the reason) and
    recording it again. Gifts are never edited in place or deleted. Members
    see only their own.
    """

    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filterset_fields = ['type', 'method', 'status', 'fiscal_year']
    search_fields = ['reference', 'member__first_name', 'member__last_name']
    ordering_fields = ['date', 'amount', 'created_at']
    
    def get_serializer_class(self):
        """Use appropriate serializer based on action."""
        if self.action == 'list':
            return PaymentListSerializer
        if self.action == 'partial_update':
            return PaymentNotesSerializer
        return PaymentSerializer

    def perform_create(self, serializer):
        """Recorded gifts are in GHS, completed unless stated, with a reference and fiscal year."""
        date = serializer.validated_data.get('date') or timezone.now()
        payment = serializer.save(
            reference=serializer.validated_data.get('reference') or _new_reference(),
            status=serializer.validated_data.get('status', 'completed'),
            currency='GHS',
            date=date,
            fiscal_year=date.year,
        )
        logger.info('payment_recorded', extra={'payment_id': payment.pk, 'actor_id': self.request.user.pk})

    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        """
        Reverse a gift recorded by mistake (staff). It stays in the history as
        "refunded" with the reason; record the correct gift separately.

        POST /api/v1/payments/:id/reverse/   Body: { "reason": "..." }
        """
        reason = (request.data.get('reason') or '').strip()
        if not reason:
            return Response({'success': False, 'error': 'Give a reason for reversing this gift.'},
                            status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(pk=self.get_object().pk)
            if payment.status != 'completed':
                return Response({'success': False, 'error': 'Only a completed gift can be reversed.'},
                                status=status.HTTP_400_BAD_REQUEST)
            stamp = timezone.now().strftime('%Y-%m-%d')
            note = f'Reversed {stamp} by {request.user.name}: {reason}'
            payment.status = 'refunded'
            payment.notes = NEWLINE.join(part for part in (payment.notes, note) if part)
            payment.save(update_fields=['status', 'notes', 'updated_at'])
        logger.info('payment_reversed', extra={'payment_id': payment.pk, 'actor_id': request.user.pk})
        return Response(PaymentSerializer(payment).data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Completed giving for one year: total, count, by month and by type.
        Staff see the church; a member sees their own.

        GET /api/v1/payments/summary/?year=2026
        """
        try:
            year = int(request.query_params.get('year') or timezone.now().year)
        except ValueError:
            return Response({'success': False, 'error': 'year must be a number.'},
                            status=status.HTTP_400_BAD_REQUEST)
        # order_by() drops the default date ordering, which would otherwise split the GROUP BY per day.
        completed = self.get_queryset().filter(status='completed', date__year=year).order_by()
        totals = completed.aggregate(total=Sum('amount'), count=Count('id'))
        by_month = {row['month']: row['total'] for row in
                    completed.annotate(month=ExtractMonth('date')).values('month').annotate(total=Sum('amount'))}
        by_type = {row['type']: row['total'] for row in completed.values('type').annotate(total=Sum('amount'))}
        return Response({
            'year': year,
            'total': totals['total'] or Decimal('0.00'),
            'count': totals['count'],
            'by_month': [{'month': month, 'total': by_month.get(month, Decimal('0.00'))} for month in range(1, 13)],
            'by_type': by_type,
        })
    
    def get_queryset(self):
        """Church staff see every payment; a member sees only their own."""
        payments = Payment.objects.all()
        if not is_church_staff(self.request.user):
            payments = payments.filter(member__user=self.request.user)
        return payments.order_by('-date')
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get payment statistics.
        
        GET /api/v1/payments/statistics/
        """
        queryset = self.get_queryset()
        
        # Calculate totals by type
        stats = {
            'total_amount': queryset.filter(status='completed').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00'),
            'total_count': queryset.count(),
            'by_type': {},
            'by_method': {},
        }
        
        # Group by type
        for payment_type in ['tithe', 'offering', 'pledge', 'donation']:
            type_payments = queryset.filter(type=payment_type, status='completed')
            stats['by_type'][payment_type] = {
                'count': type_payments.count(),
                'amount': type_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            }
        
        # Group by method
        for method in ['cash', 'check', 'online', 'bank_transfer', 'mobile_money']:
            method_payments = queryset.filter(method=method, status='completed')
            stats['by_method'][method] = {
                'count': method_payments.count(),
                'amount': method_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            }
        
        return Response({
            'success': True,
            'statistics': stats
        })
    
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """
        Export payments to CSV.
        
        GET /api/v1/payments/export-csv/?year=2025
        """
        if not (request.user.is_church_admin or request.user.is_superadmin):
            return Response({
                'success': False,
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        year = request.query_params.get('year')
        queryset = self.filter_queryset(self.get_queryset())
        
        if year:
            queryset = queryset.filter(fiscal_year=year)
        
        church_name = request.user.church.name if request.user.church else None
        return ExportService.export_payments_csv(queryset, church_name, year)


class PledgeViewSet(viewsets.ModelViewSet):
    """Pledge management viewset."""
    
    queryset = Pledge.objects.all()
    serializer_class = PledgeSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filterset_fields = ['status', 'frequency']
    ordering_fields = ['start_date', 'amount']
    
    def get_queryset(self):
        """Filter pledges by current tenant."""
        pledges = Pledge.objects.all()
        if not is_church_staff(self.request.user):
            pledges = pledges.filter(member__user=self.request.user)
        return pledges.order_by('-created_at')


class TaxReceiptViewSet(viewsets.ModelViewSet):
    """Tax receipt management viewset."""
    
    queryset = TaxReceipt.objects.all()
    serializer_class = TaxReceiptSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['fiscal_year']
    ordering_fields = ['fiscal_year', 'generated_at']
    
    def get_queryset(self):
        """Filter tax receipts."""
        user = self.request.user
        if user.is_church_admin or user.is_superadmin:
            return TaxReceipt.objects.all()
        # Members can only see their own receipts
        return TaxReceipt.objects.filter(member__user=user)
