"""
Platform admin API: manage churches, plans and subscription payments across
the whole platform. Platform superadmins only; every action is logged with the
admin's id. The rules themselves live in apps.churches.subscriptions.
"""
import logging
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.churches import provisioning, subscriptions
from apps.churches.models import Church
from apps.churches.models_plan import PLAN_CURRENCY, Plan
from apps.churches.models_subscription_payment import SubscriptionPayment
from core.permissions import IsSuperAdmin

from .models import DemoRequest
from .serializers import (CreateChurchSerializer, ExtendTrialSerializer, PlatformChurchSerializer,
                          PlatformDemoRequestSerializer,
                          PlatformPaymentSerializer, PlatformPlanSerializer, RecordPaymentSerializer,
                          SetFlagSerializer)

logger = logging.getLogger(__name__)

ACCOUNT_STATES = ('trial', 'trial_ended', 'paying', 'lapsed', 'free', 'suspended')
RECENT_PAYMENTS_SHOWN = 10


def log_action(request, action_name, church=None, **details):
    logger.info('platform_admin_action', extra={
        'action': action_name, 'actor_id': request.user.id,
        'church_id': getattr(church, 'id', None), **details,
    })


class PlatformOverviewView(APIView):
    """GET /api/v1/platform/overview/: headline numbers for the platform."""

    permission_classes = [IsSuperAdmin]

    def get(self, request):
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        churches = Church.objects.exclude(schema_name='public')
        completed_this_month = SubscriptionPayment.objects.filter(
            status='completed', completed_at__gte=month_start)
        return Response({
            'currency': PLAN_CURRENCY,
            'churches_total': churches.count(),
            'churches_new_this_month': churches.filter(created_at__gte=month_start).count(),
            'churches_by_state': {
                state: churches.filter(subscriptions.account_state_filter(state, now)).count()
                for state in ACCOUNT_STATES
            },
            'trials_ending_within_7_days': churches.filter(
                subscriptions.account_state_filter('trial', now),
                trial_end_date__lte=now + timedelta(days=7)).count(),
            'revenue_this_month': completed_this_month.aggregate(total=Sum('amount'))['total'] or 0,
            'payments_this_month': completed_this_month.count(),
        })


class PlatformChurchViewSet(viewsets.ReadOnlyModelViewSet):
    """
    /api/v1/platform/churches/            list (?search=, ?state=trial|trial_ended|paying|lapsed|free|suspended)
    /api/v1/platform/churches/:id/        detail, with recent payments
    POST /api/v1/platform/churches/       create a church on a trial and invite its admin
                                          {church_name, subdomain, denomination?, admin_name, admin_email, demo_request?}
    POST :id/resend-invite/   new invite for admins who have never signed in
    POST :id/record-payment/  {plan, duration, method, reference, amount?, note?}
    POST :id/extend-trial/    {days}
    POST :id/suspend/         {enabled}
    POST :id/free-access/     {enabled}
    """

    permission_classes = [IsSuperAdmin]
    serializer_class = PlatformChurchSerializer

    def get_queryset(self):
        churches = (Church.objects.exclude(schema_name='public')
                    .annotate(user_count=Count('users', distinct=True))
                    .order_by('-created_at'))
        search = self.request.query_params.get('search', '').strip()
        if search:
            churches = churches.filter(Q(name__icontains=search) | Q(subdomain__icontains=search)
                                       | Q(email__icontains=search))
        state = self.request.query_params.get('state')
        if state in ACCOUNT_STATES:
            churches = churches.filter(subscriptions.account_state_filter(state))
        return churches

    def retrieve(self, request, *args, **kwargs):
        church = self.get_object()
        payments = church.subscription_payments.select_related('recorded_by')[:RECENT_PAYMENTS_SHOWN]
        return Response({
            **self.get_serializer(church).data,
            'recent_payments': PlatformPaymentSerializer(payments, many=True).data,
        })

    def create(self, request, *args, **kwargs):
        form = CreateChurchSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        data = form.validated_data
        try:
            church, admin = provisioning.create_church_with_admin(
                church_name=data['church_name'], subdomain=data['subdomain'],
                denomination=data.get('denomination', ''), admin_name=data['admin_name'],
                admin_email=data['admin_email'])
        except provisioning.ProvisioningError as error:
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        demo_request = data.get('demo_request')
        if demo_request is not None:
            demo_request.church = church
            demo_request.status = 'trial'
            demo_request.save(update_fields=['church', 'status', 'updated_at'])
        invite_sent = provisioning.send_church_admin_invite(admin, church)
        log_action(request, 'create_church', church, admin_id=admin.pk, invite_sent=invite_sent,
                   demo_request_id=getattr(demo_request, 'pk', None))
        return Response({'church': self._church_response(church), 'invite_sent': invite_sent},
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='resend-invite')
    def resend_invite(self, request, pk=None):
        church = self.get_object()
        admins = church.users.filter(role='admin', is_active=True, last_login__isnull=True)
        sent = sum(provisioning.send_church_admin_invite(admin, church) for admin in admins)
        log_action(request, 'resend_church_invite', church, sent=sent)
        if not admins:
            return Response({'error': 'Every admin of this church has already signed in.'},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({'sent': sent})

    def _church_response(self, church):
        church = self.get_queryset().get(pk=church.pk)
        return self.get_serializer(church).data

    @action(detail=True, methods=['post'], url_path='record-payment')
    def record_payment(self, request, pk=None):
        church = self.get_object()
        form = RecordPaymentSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        data = form.validated_data
        try:
            payment, created = subscriptions.record_manual_payment(
                church, plan_code=data['plan'], duration=data['duration'], reference=data['reference'],
                method=data['method'], actor=request.user, amount=data.get('amount'),
                note=data.get('note', ''))
        except subscriptions.PaymentReferenceConflict as error:
            return Response({'error': str(error)}, status=status.HTTP_409_CONFLICT)
        except subscriptions.SubscriptionActionError as error:
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        log_action(request, 'record_payment', church, payment_id=payment.id, new_payment=created)
        return Response({
            'payment': PlatformPaymentSerializer(payment).data,
            'church': self._church_response(church),
            'already_recorded': not created,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='extend-trial')
    def extend_trial(self, request, pk=None):
        church = self.get_object()
        form = ExtendTrialSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        try:
            subscriptions.extend_trial(church, form.validated_data['days'])
        except subscriptions.SubscriptionActionError as error:
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        log_action(request, 'extend_trial', church, days=form.validated_data['days'])
        return Response({'church': self._church_response(church)})

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        church = self.get_object()
        form = SetFlagSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        subscriptions.set_suspended(church, form.validated_data['enabled'])
        log_action(request, 'suspend', church, enabled=form.validated_data['enabled'])
        return Response({'church': self._church_response(church)})

    @action(detail=True, methods=['post'], url_path='free-access')
    def free_access(self, request, pk=None):
        church = self.get_object()
        form = SetFlagSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        subscriptions.set_free_access(church, form.validated_data['enabled'])
        log_action(request, 'free_access', church, enabled=form.validated_data['enabled'])
        return Response({'church': self._church_response(church)})


class PlatformPlanViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                          mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """
    /api/v1/platform/plans/  list (all plans, including hidden and retired) and create
    /api/v1/platform/plans/:id/  retrieve and update. Plans are never deleted: retire
    them with is_active=false, because churches and payments refer to them.
    """

    permission_classes = [IsSuperAdmin]
    serializer_class = PlatformPlanSerializer
    queryset = Plan.objects.all()
    pagination_class = None  # a handful of plans

    def perform_create(self, serializer):
        plan = serializer.save()
        log_action(self.request, 'create_plan', plan_id=plan.id)

    def perform_update(self, serializer):
        plan = serializer.save()
        log_action(self.request, 'update_plan', plan_id=plan.id)


class PlatformPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """/api/v1/platform/payments/: all subscription payments, newest first (?church=:id, ?status=)."""

    permission_classes = [IsSuperAdmin]
    serializer_class = PlatformPaymentSerializer

    def get_queryset(self):
        payments = SubscriptionPayment.objects.select_related('church', 'recorded_by').order_by('-created_at')
        church_id = self.request.query_params.get('church')
        if church_id and church_id.isdigit():
            payments = payments.filter(church_id=int(church_id))
        payment_status = self.request.query_params.get('status')
        if payment_status:
            payments = payments.filter(status=payment_status)
        return payments


class PlatformDemoRequestViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                                 mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    /api/v1/platform/demo-requests/        list (?status=new|contacted|demo_booked|trial|paying|lost)
    /api/v1/platform/demo-requests/:id/    retrieve, PATCH {status, notes, church}, DELETE

    Personal data: every read and change is logged with the admin's id.
    """

    permission_classes = [IsSuperAdmin]
    serializer_class = PlatformDemoRequestSerializer

    def get_queryset(self):
        requests_ = DemoRequest.objects.select_related('church')
        wanted = self.request.query_params.get('status')
        if wanted:
            requests_ = requests_.filter(status=wanted)
        return requests_

    def list(self, request, *args, **kwargs):
        log_action(request, 'list_demo_requests', purpose='lead_follow_up')
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        log_action(request, 'view_demo_request', purpose='lead_follow_up', demo_request_id=kwargs.get('pk'))
        return super().retrieve(request, *args, **kwargs)

    def perform_update(self, serializer):
        demo_request = serializer.save()
        log_action(self.request, 'update_demo_request', demo_request_id=demo_request.pk,
                   status=demo_request.status)

    def perform_destroy(self, instance):
        log_action(self.request, 'delete_demo_request', demo_request_id=instance.pk)
        instance.delete()
