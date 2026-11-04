import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0008_execution_recovery_record"),
    ]

    operations = [
        migrations.AddField(
            model_name="automationjob",
            name="runner_id",
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="automationjob",
            name="runner_pid",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="automationjob",
            name="runner_start_ticks",
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="automationjob",
            name="runner_container_boot_id",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="automationjob",
            name="runner_pgid",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="automationjob",
            name="runner_profile_path",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="automationjob",
            name="runner_ipc_path",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="automationjob",
            name="runner_state",
            field=models.CharField(blank=True, db_index=True, max_length=32),
        ),
        migrations.AddField(
            model_name="automationjob",
            name="runner_heartbeat_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="accountbrowserlock",
            name="runner_id",
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="accountbrowserlock",
            name="runner_pid",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="accountbrowserlock",
            name="runner_start_ticks",
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="accountbrowserlock",
            name="runner_container_boot_id",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="accountbrowserlock",
            name="runner_pgid",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="accountbrowserlock",
            name="runner_profile_path",
            field=models.TextField(blank=True),
        ),
    ]
