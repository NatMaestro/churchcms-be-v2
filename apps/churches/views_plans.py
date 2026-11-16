"""
Public list of subscription plans, for the landing page and pricing screens.

Unauthenticated and read-only: shows the plans a platform admin marked active
and public, with their GHS prices. Nothing church-specific is returned.
"""
from rest_framework import permissions, serializers
from rest_framework.decorators import (api_view, authentication_classes, permission_classes,
                                       throttle_classes)
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models_plan import PLAN_CURRENCY, Plan

PUBLIC_PLANS_VERSION = 1


class PublicPlansThrottle(AnonRateThrottle):
    """Per-IP limit on the public plan list (rate set in settings)."""

    scope = 'public_plans'


class PublicPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ['code', 'name', 'tagline', 'price_monthly', 'price_yearly',
                  'member_limit', 'features', 'is_featured']


@api_view(['GET'])
@authentication_classes([])  # public: a stale login cookie must not turn this into a 401
@permission_classes([permissions.AllowAny])
@throttle_classes([PublicPlansThrottle])
def public_plans(request):
    """
    GET /api/v1/plans/

    {"version": 1, "currency": "GHS", "plans": [{code, name, tagline, price_monthly,
     price_yearly, member_limit, features, is_featured}, ...]}
    """
    plans = Plan.objects.filter(is_active=True, is_public=True)
    return Response({
        'version': PUBLIC_PLANS_VERSION,
        'currency': PLAN_CURRENCY,
        'plans': PublicPlanSerializer(plans, many=True).data,
    })
