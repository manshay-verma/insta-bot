from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0007_atomic_execution_recovery"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExecutionRecoveryRecord",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("failed_generation", models.PositiveIntegerField(db_index=True)),
                (
                    "recovery_kind",
                    models.CharField(db_index=True, max_length=32),
                ),
                (
                    "recovery_delivery_key",
                    models.CharField(max_length=128, unique=True),
                ),
                ("allocated_generation", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="execution_recovery_records",
                        to="api.automationjob",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("job", "failed_generation", "recovery_kind"),
                        name="unique_job_failed_generation_recovery_kind",
                    ),
                ],
            },
        ),
    ]
