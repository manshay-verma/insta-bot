import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("account", "0002_botaccount_owner"),
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AutomationJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(max_length=32)),
                ("targets", models.JSONField(default=list)),
                ("options", models.JSONField(blank=True, default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("retrying", "Retrying"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                            ("cancelling", "Cancelling"),
                            ("cancelled", "Cancelled"),
                        ],
                        db_index=True,
                        default="queued",
                        max_length=16,
                    ),
                ),
                ("celery_task_id", models.CharField(blank=True, db_index=True, max_length=255)),
                ("idempotency_key", models.CharField(blank=True, max_length=128, null=True)),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                ("result", models.JSONField(blank=True, null=True)),
                ("error", models.TextField(blank=True)),
                ("cancel_requested", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="automation_jobs",
                        to="account.botaccount",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="automation_jobs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="automationjob",
            constraint=models.UniqueConstraint(
                condition=models.Q(("idempotency_key__isnull", False)),
                fields=("user", "idempotency_key"),
                name="unique_user_automation_idempotency_key",
            ),
        ),
        migrations.AddConstraint(
            model_name="automationjob",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ("status__in", ["queued", "running", "retrying", "cancelling"])
                ),
                fields=("account",),
                name="one_active_automation_job_per_account",
            ),
        ),
    ]
