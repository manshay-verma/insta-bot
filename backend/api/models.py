import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class AppSetting(models.Model):
    """
    Lightweight persisted settings for one dashboard user.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="app_settings",
    )
    theme = models.CharField(max_length=20, default="dark")
    notifications = models.JSONField(default=dict, blank=True)
    proxy_settings = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner"],
                condition=Q(owner__isnull=False),
                name="unique_owner_app_setting",
            ),
        ]


class ExportJob(models.Model):
    """Track export generation and provide a download link."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="export_jobs",
    )
    STATUS_CHOICES = [
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    export_format = models.CharField(max_length=20)  # json | csv | zip
    data_types = models.JSONField(default=list, blank=True)
    filename = models.CharField(max_length=255)
    file_path = models.TextField()
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="completed")
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class AutomationJob(models.Model):
    """Durable application-level state for a queued automation request."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        RETRYING = "retrying", "Retrying"
        AWAITING_OTP = "awaiting_otp", "Awaiting verification code"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLING = "cancelling", "Cancelling"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="automation_jobs",
    )
    account = models.ForeignKey(
        "account.BotAccount",
        on_delete=models.CASCADE,
        related_name="automation_jobs",
    )
    action = models.CharField(max_length=32)
    targets = models.JSONField(default=list)
    options = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
    )
    celery_task_id = models.CharField(max_length=255, blank=True, db_index=True)
    idempotency_key = models.CharField(max_length=128, null=True, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    cancel_requested = models.BooleanField(default=False)
    verification_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "idempotency_key"],
                condition=Q(idempotency_key__isnull=False),
                name="unique_user_automation_idempotency_key",
            ),
            models.UniqueConstraint(
                fields=["account"],
                condition=Q(
                    status__in=[
                        "queued",
                        "running",
                        "retrying",
                        "awaiting_otp",
                        "cancelling",
                    ]
                ),
                name="one_active_automation_job_per_account",
            ),
        ]
