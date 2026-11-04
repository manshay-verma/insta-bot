from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0004_merge_20261009_2159"),
        ("account", "0003_cookie_session_metadata"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountBrowserLock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("owner_token_hash", models.CharField(editable=False, max_length=64)),
                ("acquired_at", models.DateTimeField(auto_now_add=True)),
                ("renewed_at", models.DateTimeField(auto_now=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("account", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="browser_lock", to="account.botaccount")),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="browser_locks", to="api.automationjob")),
            ],
            options={"ordering": ["-renewed_at"]},
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=r"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_indexes
                            WHERE indexname = 'one_active_automation_job_per_account'
                        ) THEN
                            CREATE UNIQUE INDEX one_active_automation_job_per_account
                            ON api_automationjob(account_id)
                            WHERE status IN ('queued', 'running', 'retrying', 'awaiting_otp', 'cancelling');
                        END IF;
                    END $$;
                    """,
                    reverse_sql="""
                    DROP INDEX IF EXISTS one_active_automation_job_per_account;
                    """,
                ),
            ],
            state_operations=[],
        ),
    ]
