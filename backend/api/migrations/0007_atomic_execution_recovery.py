from django.db import migrations, models
import django.db.models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0006_execution_generation_fencing"),
    ]

    operations = [
        migrations.AddField(
            model_name="automationjob",
            name="recovery_delivery_key",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=128,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="automationjob",
            name="recovery_generation",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AddConstraint(
            model_name="automationjob",
            constraint=models.UniqueConstraint(
                condition=django.db.models.Q(
                    ("recovery_delivery_key__isnull", False),
                ),
                fields=("recovery_delivery_key",),
                name="unique_automation_recovery_delivery",
            ),
        ),
    ]
