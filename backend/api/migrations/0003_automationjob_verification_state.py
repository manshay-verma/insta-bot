from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_automationjob"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="automationjob",
            name="one_active_automation_job_per_account",
        ),
        migrations.AlterField(
            model_name="automationjob",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("running", "Running"),
                    ("retrying", "Retrying"),
                    ("awaiting_otp", "Awaiting verification code"),
                    ("succeeded", "Succeeded"),
                    ("failed", "Failed"),
                    ("cancelling", "Cancelling"),
                    ("cancelled", "Cancelled"),
                ],
                db_index=True,
                default="queued",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="automationjob",
            name="verification_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="automationjob",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    status__in=[
                        "queued",
                        "running",
                        "retrying",
                        "awaiting_otp",
                        "cancelling",
                    ]
                ),
                fields=("account",),
                name="one_active_automation_job_per_account",
            ),
        ),
    ]
