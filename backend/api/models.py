from django.db import models


class AppSetting(models.Model):
    """
    Lightweight persisted settings for the dashboard.

    We keep this as a single-row table (one environment) to avoid complex user management
    while still making the Settings page fully dynamic.
    """

    theme = models.CharField(max_length=20, default="dark")
    notifications = models.JSONField(default=dict, blank=True)
    proxy_settings = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class ExportJob(models.Model):
    """Track export generation and provide a download link."""

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

