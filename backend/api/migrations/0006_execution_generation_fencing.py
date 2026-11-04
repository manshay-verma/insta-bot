import django.db.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0005_accountbrowserlock_and_constraint"),
    ]

    operations = [
        migrations.AddField(
            model_name="automationjob",
            name="application_retry_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="automationjob",
            name="execution_generation",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AddField(
            model_name="automationjob",
            name="recovery_state",
            field=models.CharField(db_index=True, default="none", max_length=32),
        ),
        migrations.AddField(
            model_name="automationjob",
            name="worker_redelivery_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="accountbrowserlock",
            name="execution_generation",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
    ]
