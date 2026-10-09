from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.utils import timezone
from django.db import models
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAdminUser
from datetime import timedelta

from .models import Proxy, BotAccount, Session
from api.openapi import (
    ApiErrorSchema,
    CookieUpdateRequestSchema,
    StatusMessageResponseSchema,
)
from .serializers import (
    ProxySerializer,
    BotAccountSerializer,
    BotAccountCreateSerializer,
    SessionSerializer,
    AccountHealthSerializer,
)


class ProxyViewSet(viewsets.ModelViewSet):
    """ViewSet for Proxy CRUD operations."""
    queryset = Proxy.objects.all()
    serializer_class = ProxySerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset


def _is_worker_request(request):
    return getattr(request, "auth", None) == "worker"


def _user_accounts(request):
    if _is_worker_request(request) or request.user.is_staff:
        return BotAccount.objects.all()
    return BotAccount.objects.filter(owner=request.user)


class BotAccountViewSet(viewsets.ModelViewSet):
    """ViewSet for BotAccount CRUD operations."""
    queryset = BotAccount.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return BotAccountCreateSerializer
        return BotAccountSerializer

    def get_queryset(self):
        queryset = _user_accounts(self.request).select_related('proxy')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['get'])
    def health(self, request, pk=None):
        """Get health status for a specific account."""
        account = self.get_object()
        today = timezone.now().date()

        sessions_today = Session.objects.filter(
            account=account,
            started_at__date=today
        ).count()

        actions_today = Session.objects.filter(
            account=account,
            started_at__date=today
        ).aggregate(total=models.Sum('actions_count'))['total'] or 0

        is_healthy = (
            account.status == 'active' and
            float(account.trust_score) >= 0.3 and
            sessions_today < 10
        )

        health_data = {
            'account_id': account.id,
            'username': account.username,
            'status': account.status,
            'trust_score': account.trust_score,
            'last_login': account.last_login,
            'sessions_today': sessions_today,
            'actions_today': actions_today,
            'is_healthy': is_healthy,
        }

        serializer = AccountHealthSerializer(health_data)
        return Response(serializer.data)

    @extend_schema(
        request=CookieUpdateRequestSchema,
        responses={200: StatusMessageResponseSchema, 400: ApiErrorSchema},
    )
    @action(detail=True, methods=['post'])
    def update_cookies(self, request, pk=None):
        """Update session cookies for an account."""
        account = self.get_object()
        cookies = request.data.get('cookies')
        if cookies:
            account.cookies_json = cookies
            account.last_login = timezone.now()
            account.save()
            return Response({'status': 'cookies updated'})
        return Response(
            {'error': 'cookies field required'},
            status=status.HTTP_400_BAD_REQUEST
        )


class SessionViewSet(viewsets.ModelViewSet):
    """ViewSet for Session operations."""
    queryset = Session.objects.all()
    serializer_class = SessionSerializer

    def get_queryset(self):
        if _is_worker_request(self.request) or self.request.user.is_staff:
            queryset = Session.objects.all()
        else:
            queryset = Session.objects.filter(account__owner=self.request.user)
        account_id = self.request.query_params.get('account')
        if account_id:
            queryset = queryset.filter(account_id=account_id)
        return queryset

    def perform_create(self, serializer):
        account = serializer.validated_data["account"]
        if not _is_worker_request(self.request) and not self.request.user.is_staff:
            if account.owner_id != self.request.user.id:
                raise PermissionDenied("You do not have access to this bot account.")
        serializer.save()

    def perform_update(self, serializer):
        account = serializer.validated_data.get(
            "account",
            serializer.instance.account,
        )
        if not _is_worker_request(self.request) and not self.request.user.is_staff:
            if account.owner_id != self.request.user.id:
                raise PermissionDenied("You do not have access to this bot account.")
        serializer.save()

    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        """End an active session."""
        session = self.get_object()
        if session.status == 'active':
            session.status = 'completed'
            session.ended_at = timezone.now()
            session.save()
            return Response({'status': 'session ended'})
        return Response(
            {'error': 'session not active'},
            status=status.HTTP_400_BAD_REQUEST
        )
