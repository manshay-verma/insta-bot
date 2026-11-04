import base64
import hashlib
import json
import os
import time

from cryptography.fernet import Fernet
from django.db import migrations, models


def migrate_existing_cookies(apps, schema_editor):
    BotAccount = apps.get_model("account", "BotAccount")
    secret = os.environ.get(
        "INSTABOT_COOKIE_ENCRYPTION_KEY",
        os.environ.get("DJANGO_SECRET_KEY", "default-secret-key-change-in-production"),
    )
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    fernet = Fernet(key)

    for account in BotAccount.objects.exclude(cookies_json=None).iterator():
        raw = account.cookies_json
        cookies = raw.get("cookies") if isinstance(raw, dict) else raw
        valid = isinstance(cookies, list) and bool(cookies)
        if valid:
            names = {
                cookie.get("name")
                for cookie in cookies
                if isinstance(cookie, dict)
            }
            domains = {
                str(cookie.get("domain", "")).lower()
                for cookie in cookies
                if isinstance(cookie, dict)
            }
            valid = "sessionid" in names and "csrftoken" in names and bool(domains.intersection({
                "instagram.com",
                ".instagram.com",
            })) or bool([
                domain for domain in domains
                if domain.endswith(".instagram.com")
            ])
            if valid:
                for cookie in cookies:
                    if isinstance(cookie, dict):
                        expires = cookie.get("expires")
                        if isinstance(expires, (int, float)) and expires > 0 and expires <= time.time():
                            valid = False
                            break
        if valid:
            payload = json.dumps(cookies, separators=(",", ":"), ensure_ascii=True).encode()
            account.cookies_encrypted = fernet.encrypt(payload).decode()
            account.cookies_json = None
            account.session_status = "valid"
            account.cookie_version = 1
            account.cookie_updated_at = account.updated_at
            account.cookie_validated_at = account.updated_at
            account.save(update_fields=[
                "cookies_encrypted",
                "cookies_json",
                "session_status",
                "cookie_version",
                "cookie_updated_at",
                "cookie_validated_at",
            ])
        else:
            account.cookies_json = None
            account.cookies_encrypted = None
            account.session_status = "invalid"
            account.cookie_validated_at = account.updated_at
            account.save(update_fields=[
                "cookies_json",
                "cookies_encrypted",
                "session_status",
                "cookie_validated_at",
            ])


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0002_botaccount_owner"),
    ]

    operations = [
        migrations.AddField(
            model_name="botaccount",
            name="cookies_encrypted",
            field=models.TextField(blank=True, help_text="Encrypted session cookies", null=True),
        ),
        migrations.AddField(
            model_name="botaccount",
            name="session_status",
            field=models.CharField(
                choices=[
                    ("missing", "Missing"),
                    ("login_required", "Login required"),
                    ("valid", "Valid"),
                    ("expired", "Expired"),
                    ("invalid", "Invalid"),
                    ("verification_required", "Verification required"),
                ],
                db_index=True,
                default="missing",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="botaccount",
            name="cookie_version",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="botaccount",
            name="cookie_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="botaccount",
            name="cookie_validated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(migrate_existing_cookies, migrations.RunPython.noop),
    ]
