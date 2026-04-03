from rest_framework import serializers
from .models import DailyAnalytics, ActionLog, UserBehavior


class DailyAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for DailyAnalytics model."""
    account_username = serializers.CharField(source='account.username', read_only=True)

    class Meta:
        model = DailyAnalytics
        fields = [
            'id', 'date', 'account', 'account_username',
            'follows_count', 'unfollows_count', 'likes_count',
            'comments_count', 'downloads_count', 'profiles_explored',
            'stories_viewed', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ActionLogSerializer(serializers.ModelSerializer):
    """Serializer for ActionLog model."""
    account_username = serializers.CharField(source='account.username', read_only=True)

    class Meta:
        model = ActionLog
        fields = [
            'id', 'account', 'account_username', 'session',
            'action_type', 'target_username', 'target_url',
            'success', 'error_message', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ActionLogCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating action logs."""

    class Meta:
        model = ActionLog
        fields = [
            'account', 'session', 'action_type',
            'target_username', 'target_url', 'success',
            'error_message', 'metadata'
        ]


class UserBehaviorSerializer(serializers.ModelSerializer):
    """Serializer for UserBehavior model."""
    account_username = serializers.CharField(source='account.username', read_only=True)

    class Meta:
        model = UserBehavior
        fields = ['id', 'account', 'account_username', 'behavior_type', 'data', 'recorded_at']
        read_only_fields = ['id', 'recorded_at']


class DashboardSummarySerializer(serializers.Serializer):
    """Serializer for dashboard summary response."""
    total_accounts = serializers.IntegerField()
    active_accounts = serializers.IntegerField()
    total_follows_today = serializers.IntegerField()
    total_likes_today = serializers.IntegerField()
    total_downloads_today = serializers.IntegerField()
    total_actions_today = serializers.IntegerField()


class AccountStatsSerializer(serializers.Serializer):
    """Serializer for per-account stats."""
    account_id = serializers.IntegerField()
    username = serializers.CharField()
    follows_today = serializers.IntegerField()
    likes_today = serializers.IntegerField()
    actions_today = serializers.IntegerField()
    trust_score = serializers.DecimalField(max_digits=3, decimal_places=2)
