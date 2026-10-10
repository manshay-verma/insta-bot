from rest_framework import serializers

from account.models import BotAccount
from .models import AutomationJob


class AutomationJobCreateSerializer(serializers.Serializer):
    account_id = serializers.IntegerField(min_value=1)
    action = serializers.ChoiceField(
        choices=[
            "like",
            "follow",
            "unfollow",
            "scrape_profile",
            "view_stories",
            "download",
            "comment",
        ]
    )
    targets = serializers.ListField(
        child=serializers.CharField(trim_whitespace=True, allow_blank=False),
        min_length=1,
    )
    options = serializers.DictField(required=False, default=dict)

    def validate_options(self, options):
        blocked_keys = {
            "password",
            "ig_password",
            "cookie",
            "cookies",
            "token",
            "secret",
            "verification_callback",
        }

        def contains_sensitive_key(value):
            if isinstance(value, dict):
                return any(
                    any(part in key.lower() for part in blocked_keys)
                    or contains_sensitive_key(item)
                    for key, item in value.items()
                )
            if isinstance(value, list):
                return any(contains_sensitive_key(item) for item in value)
            return False

        if contains_sensitive_key(options):
            raise serializers.ValidationError(
                "Credentials and session data must not be sent in job options."
            )
        return options


class VerificationCodeSubmitSerializer(serializers.Serializer):
    code = serializers.RegexField(
        regex=r"^\d{4,10}$",
        max_length=10,
        trim_whitespace=True,
        write_only=True,
    )


class AutomationJobStatusSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(source="id", read_only=True)
    task_id = serializers.CharField(source="celery_task_id", read_only=True)

    class Meta:
        model = AutomationJob
        fields = [
            "job_id",
            "task_id",
            "account",
            "action",
            "status",
            "attempt_count",
            "result",
            "error",
            "cancel_requested",
            "verification_expires_at",
            "created_at",
            "started_at",
            "completed_at",
        ]
        read_only_fields = fields
