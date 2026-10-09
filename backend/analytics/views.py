from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta

from .models import DailyAnalytics, ActionLog, UserBehavior
from .serializers import (
    DailyAnalyticsSerializer,
    ActionLogSerializer,
    ActionLogCreateSerializer,
    UserBehaviorSerializer,
    DashboardSummarySerializer,
    AccountStatsSerializer,
)
from account.models import BotAccount


def _can_access_account(request, account):
    return request.user.is_staff or (
        getattr(request, "auth", None) == "worker"
        or account.owner_id == request.user.id
    )


class DailyAnalyticsViewSet(viewsets.ModelViewSet):
    """ViewSet for DailyAnalytics CRUD operations."""
    queryset = DailyAnalytics.objects.all()
    serializer_class = DailyAnalyticsSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(account__owner=self.request.user)
        account_id = self.request.query_params.get('account')
        if account_id:
            queryset = queryset.filter(account_id=account_id)
        
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset

    def perform_create(self, serializer):
        if not _can_access_account(self.request, serializer.validated_data["account"]):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not have access to this bot account.")
        serializer.save()

    def perform_update(self, serializer):
        account = serializer.validated_data.get("account", serializer.instance.account)
        if not _can_access_account(self.request, account):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not have access to this bot account.")
        serializer.save()


class ActionLogViewSet(viewsets.ModelViewSet):
    """ViewSet for ActionLog operations."""
    queryset = ActionLog.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return ActionLogCreateSerializer
        return ActionLogSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff and getattr(self.request, "auth", None) != "worker":
            queryset = queryset.filter(account__owner=self.request.user)
        account_id = self.request.query_params.get('account')
        if account_id:
            queryset = queryset.filter(account_id=account_id)
        
        action_type = self.request.query_params.get('action_type')
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        
        success = self.request.query_params.get('success')
        if success is not None:
            queryset = queryset.filter(success=success.lower() == 'true')
        
        return queryset

    def perform_create(self, serializer):
        account = serializer.validated_data["account"]
        if not _can_access_account(self.request, account):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not have access to this bot account.")
        serializer.save()

    def perform_update(self, serializer):
        account = serializer.validated_data.get("account", serializer.instance.account)
        if not _can_access_account(self.request, account):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not have access to this bot account.")
        serializer.save()


class UserBehaviorViewSet(viewsets.ModelViewSet):
    """ViewSet for UserBehavior operations."""
    queryset = UserBehavior.objects.all()
    serializer_class = UserBehaviorSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(account__owner=self.request.user)
        account_id = self.request.query_params.get('account')
        if account_id:
            queryset = queryset.filter(account_id=account_id)
        return queryset

    def perform_create(self, serializer):
        if not _can_access_account(self.request, serializer.validated_data["account"]):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not have access to this bot account.")
        serializer.save()

    def perform_update(self, serializer):
        account = serializer.validated_data.get("account", serializer.instance.account)
        if not _can_access_account(self.request, account):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not have access to this bot account.")
        serializer.save()


class DashboardView(APIView):
    """Dashboard summary endpoint."""

    def get(self, request):
        today = timezone.now().date()
        accounts = BotAccount.objects.all()
        if not request.user.is_staff:
            accounts = accounts.filter(owner=request.user)

        today_stats = DailyAnalytics.objects.filter(
            account__in=accounts,
            date=today,
        ).aggregate(
            total_follows=Sum('follows_count'),
            total_likes=Sum('likes_count'),
            total_downloads=Sum('downloads_count'),
        )

        total_actions_today = ActionLog.objects.filter(
            account__in=accounts,
            created_at__date=today,
        ).count()

        data = {
            'total_accounts': accounts.count(),
            'active_accounts': accounts.filter(status='active').count(),
            'total_follows_today': today_stats['total_follows'] or 0,
            'total_likes_today': today_stats['total_likes'] or 0,
            'total_downloads_today': today_stats['total_downloads'] or 0,
            'total_actions_today': total_actions_today,
        }
        
        serializer = DashboardSummarySerializer(data)
        return Response(serializer.data)


class AccountStatsView(APIView):
    """Get stats for a specific account."""

    def get(self, request, account_id):
        try:
            accounts = BotAccount.objects.all()
            if not request.user.is_staff:
                accounts = accounts.filter(owner=request.user)
            account = accounts.get(id=account_id)
        except BotAccount.DoesNotExist:
            return Response(
                {'error': 'Account not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        today = timezone.now().date()
        today_analytics = DailyAnalytics.objects.filter(
            account=account, date=today
        ).first()
        
        actions_today = ActionLog.objects.filter(
            account=account, created_at__date=today
        ).count()
        
        data = {
            'account_id': account.id,
            'username': account.username,
            'follows_today': today_analytics.follows_count if today_analytics else 0,
            'likes_today': today_analytics.likes_count if today_analytics else 0,
            'actions_today': actions_today,
            'trust_score': account.trust_score,
        }
        
        serializer = AccountStatsSerializer(data)
        return Response(serializer.data)
