"""Serializers used to describe custom APIView/action contracts in OpenAPI.

These classes are documentation-only. Runtime request validation remains in
the existing endpoint serializers and view logic.
"""

from rest_framework import serializers


class ApiErrorSchema(serializers.Serializer):
    error = serializers.JSONField(required=False)
    detail = serializers.CharField(required=False)
    message = serializers.CharField(required=False)
    toast_type = serializers.ChoiceField(choices=("error", "warning"), required=False)
    details = serializers.JSONField(required=False)
    job_id = serializers.IntegerField(required=False)


class BotExecuteValidationErrorsSchema(serializers.Serializer):
    account_id = serializers.ListField(child=serializers.JSONField(), required=False)
    action = serializers.ListField(child=serializers.JSONField(), required=False)
    targets = serializers.ListField(child=serializers.JSONField(), required=False)
    options = serializers.ListField(child=serializers.JSONField(), required=False)
    non_field_errors = serializers.ListField(child=serializers.JSONField(), required=False)


class RegisterResponseSchema(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()


class SettingsStateSchema(serializers.Serializer):
    theme = serializers.CharField()
    notifications = serializers.DictField()
    proxy_settings = serializers.DictField()
    updated_at = serializers.DateTimeField()


class BotStatusSummarySchema(serializers.Serializer):
    total = serializers.IntegerField()
    active = serializers.IntegerField()
    paused = serializers.IntegerField()
    banned = serializers.IntegerField()
    checkpoint = serializers.IntegerField()


class RunningBotSchema(serializers.Serializer):
    account_id = serializers.IntegerField()
    username = serializers.CharField()
    session_id = serializers.IntegerField()
    started_at = serializers.DateTimeField()
    actions_count = serializers.IntegerField()


class BotStatusResponseSchema(serializers.Serializer):
    status_summary = BotStatusSummarySchema()
    running_bots = RunningBotSchema(many=True)


class BotControlRequestSchema(serializers.Serializer):
    action = serializers.ChoiceField(choices=("start", "stop", "pause", "resume"))
    account_id = serializers.IntegerField()


class BotControlBulkRequestSchema(serializers.Serializer):
    action = serializers.ChoiceField(choices=("start_all", "stop_all", "pause_all", "resume_all"))


class BotControlResponseSchema(serializers.Serializer):
    message = serializers.CharField()
    session_id = serializers.IntegerField(required=False)
    created_sessions = serializers.IntegerField(required=False)
    skipped = serializers.IntegerField(required=False)
    stopped_sessions = serializers.IntegerField(required=False)
    updated_accounts = serializers.IntegerField(required=False)


class HealthResponseSchema(serializers.Serializer):
    status = serializers.CharField()
    timestamp = serializers.DateTimeField()
    version = serializers.CharField()


class SystemStatusResponseSchema(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    uptime_seconds = serializers.IntegerField()
    active_sessions = serializers.IntegerField()
    network_health = serializers.CharField()
    cpu_usage_percent = serializers.IntegerField(allow_null=True)
    pid = serializers.IntegerField()


class UpcomingScheduleResponseSchema(serializers.Serializer):
    items = serializers.ListField(child=serializers.JSONField())


class CleanupRequestSchema(serializers.Serializer):
    cutoff_days = serializers.IntegerField(required=False, default=30)


class CleanupResponseSchema(serializers.Serializer):
    message = serializers.CharField()
    deleted_sessions = serializers.IntegerField()
    cutoff_days = serializers.IntegerField()


class RateLimitsSchema(serializers.Serializer):
    follows_per_day = serializers.IntegerField()
    likes_per_hour = serializers.IntegerField()
    stories_per_hour = serializers.IntegerField()
    scrolls_per_session = serializers.IntegerField()


class RateLimitResponseSchema(serializers.Serializer):
    account_id = serializers.CharField(required=False)
    limits = RateLimitsSchema()
    usage_today = serializers.DictField(child=serializers.IntegerField(), required=False)


class ExportCreateResponseSchema(serializers.Serializer):
    job_id = serializers.IntegerField()
    filename = serializers.CharField()
    download_url = serializers.CharField()


class ExportStatsCountsSchema(serializers.Serializer):
    accounts = serializers.IntegerField()
    sessions = serializers.IntegerField()
    action_logs = serializers.IntegerField()
    daily_analytics = serializers.IntegerField()
    downloads = serializers.IntegerField()
    media_files = serializers.IntegerField()


class ExportStatsResponseSchema(serializers.Serializer):
    total_rows = ExportStatsCountsSchema()


class BotExecutionResponseSchema(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField(required=False)
    items_processed = serializers.IntegerField()
    errors = serializers.ListField(child=serializers.CharField())


class QueuedTaskResponseSchema(serializers.Serializer):
    task_id = serializers.CharField()
    status = serializers.ChoiceField(choices=("queued",))
    message = serializers.CharField()


class CookieUpdateRequestSchema(serializers.Serializer):
    cookies = serializers.JSONField()


class StatusMessageResponseSchema(serializers.Serializer):
    status = serializers.CharField()


class TaskStatusResponseSchema(serializers.Serializer):
    task_id = serializers.CharField()
    status = serializers.CharField()
    result = serializers.JSONField(allow_null=True)


class BulkQueueResponseSchema(serializers.Serializer):
    message = serializers.CharField()
    queue_ids = serializers.ListField(child=serializers.IntegerField())


class QueueProcessResponseSchema(serializers.Serializer):
    message = serializers.CharField()
    download_id = serializers.IntegerField()
