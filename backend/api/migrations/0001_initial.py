from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AppSetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("theme", models.CharField(default="dark", max_length=20)),
                ("notifications", models.JSONField(blank=True, default=dict)),
                ("proxy_settings", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="ExportJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("export_format", models.CharField(max_length=20)),
                ("data_types", models.JSONField(blank=True, default=list)),
                ("filename", models.CharField(max_length=255)),
                ("file_path", models.TextField()),
                ("file_size_bytes", models.BigIntegerField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("completed", "Completed"), ("failed", "Failed")],
                        default="completed",
                        max_length=20,
                    ),
                ),
                ("error_message", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]

