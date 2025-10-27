"""
Payment views.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from decimal import Decimal
from .models import Payment, Pledge, TaxReceipt
from .serializers import (
    PaymentSerializer,
    PaymentListSerializer,
    PledgeSerializer,
    TaxReceiptSerializer
)
from core.permissions import IsAdminOrReadOnly
from core.services import ExportService


class PaymentViewSet(viewsets.ModelViewSet):
    """Payment management viewset."""
    
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
        return PaymentSerializer
    
    def get_queryset(self):
        """Filter payments by current tenant."""
        return Payment.objects.all().order_by('-date')
    
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
        return Pledge.objects.all().order_by('-created_at')


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
