from rest_framework import serializers
from .models import Proxy, BotAccount, Session


class ProxySerializer(serializers.ModelSerializer):
    """Serializer for Proxy model."""

    class Meta:
        model = Proxy
        fields = [
            'id', 'host', 'port', 'protocol', 'username',
            'country_code', 'failure_count', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'failure_count', 'created_at']


class BotAccountSerializer(serializers.ModelSerializer):
    """Serializer for listing bot accounts (excludes sensitive data)."""
    proxy_display = serializers.StringRelatedField(source='proxy', read_only=True)

    class Meta:
        model = BotAccount
        fields = [
            'id', 'username', 'status', 'trust_score',
            'proxy', 'proxy_display', 'last_login', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'trust_score', 'last_login', 'created_at', 'updated_at']


class BotAccountCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating bot accounts with password."""
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = BotAccount
        fields = ['id', 'username', 'password', 'proxy', 'status']
        read_only_fields = ['id']

    def create(self, validated_data):
        from .utils import encrypt_password
        password = validated_data.pop('password')
        validated_data['password_encrypted'] = encrypt_password(password)
        return super().create(validated_data)



class SessionSerializer(serializers.ModelSerializer):
    """Serializer for Session model."""
    account_username = serializers.CharField(source='account.username', read_only=True)
    duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            'id', 'account', 'account_username', 'started_at',
            'ended_at', 'actions_count', 'status', 'duration_seconds'
        ]
        read_only_fields = ['id', 'started_at', 'duration_seconds']

    def get_duration_seconds(self, obj):
        duration = obj.duration
        return int(duration.total_seconds()) if duration else 0


class AccountHealthSerializer(serializers.Serializer):
    """Serializer for account health response."""
    account_id = serializers.IntegerField()
    username = serializers.CharField()
    status = serializers.CharField()
    trust_score = serializers.DecimalField(max_digits=3, decimal_places=2)
    last_login = serializers.DateTimeField()
    sessions_today = serializers.IntegerField()
    actions_today = serializers.IntegerField()
    is_healthy = serializers.BooleanField()
