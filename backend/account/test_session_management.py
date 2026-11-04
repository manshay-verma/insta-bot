from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from account.models import BotAccount
from account.utils import decrypt_cookie_data, encrypt_cookie_data, normalize_and_validate_cookies
from api.account_locks import acquire_account_lock
from api.models import AutomationJob


class CookieSessionManagementTests(TestCase):
    def setUp(self):
        owner = get_user_model().objects.create_user(
            username="cookie-owner",
            password="test-password",
        )
        self.account = BotAccount.objects.create(
            owner=owner,
            username="cookie-account",
            password_encrypted="encrypted-value",
        )
        self.job = AutomationJob.objects.create(
            user=owner,
            account=self.account,
            action="login",
            targets=[],
            status=AutomationJob.Status.RUNNING,
        )
        self.account_lock = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=self.job.execution_generation,
        )
        self.lock_payload = {
            "job_id": str(self.job.id),
            "lock_owner_token": self.account_lock.owner_token,
            "execution_generation": self.job.execution_generation,
        }

    def test_new_account_starts_without_session(self):
        account = BotAccount.objects.get(pk=self.account.pk)
        self.assertEqual(account.session_status, "missing")
        self.assertEqual(account.cookie_version, 0)
        self.assertIsNone(account.cookies_encrypted)
        self.assertIsNone(account.cookies_json)

    def test_cookie_validation_rejects_missing_session_and_foreign_domain(self):
        self.assertIsNone(normalize_and_validate_cookies([]))
        self.assertIsNone(normalize_and_validate_cookies([
            {"name": "csrftoken", "value": "value", "domain": ".instagram.com"},
        ]))
        self.assertIsNone(normalize_and_validate_cookies([
            {"name": "sessionid", "value": "value", "domain": ".example.com"},
        ]))

    def test_cookie_validation_rejects_expired_cookie(self):
        self.assertIsNone(normalize_and_validate_cookies([
            {
                "name": "sessionid",
                "value": "session-value",
                "domain": ".instagram.com",
                "expires": 1,
            },
        ]))

    def test_cookie_data_is_encrypted_and_can_be_decrypted(self):
        cookies = [{"name": "sessionid", "value": "opaque-value", "domain": ".instagram.com"}]
        encrypted = encrypt_cookie_data(cookies)
        self.assertNotIn("opaque-value", encrypted)
        self.assertEqual(decrypt_cookie_data(encrypted), cookies)

    @override_settings(INSTABOT_WORKER_TOKEN="worker-test-token")
    def test_worker_api_persists_and_returns_cookie_metadata(self):
        client = APIClient()
        headers = {"HTTP_X_WORKER_TOKEN": "worker-test-token"}
        cookies = [
            {"name": "sessionid", "value": "opaque-value", "domain": ".instagram.com", "expires": -1},
            {"name": "csrftoken", "value": "csrf-value", "domain": ".instagram.com"},
        ]

        response = client.post(
            f"/api/v1/accounts/{self.account.id}/update_cookies/",
            {"cookies": cookies, **self.lock_payload},
            format="json",
            **headers,
        )

        self.assertEqual(response.status_code, 200)
        account = BotAccount.objects.get(pk=self.account.pk)
        self.assertEqual(account.session_status, "valid")
        self.assertEqual(account.cookie_version, 1)
        self.assertIsNone(account.cookies_json)
        self.assertIsNotNone(account.cookies_encrypted)

        retrieval = client.get(
            f"/api/v1/accounts/{self.account.id}/",
            **headers,
        )
        self.assertEqual(retrieval.status_code, 200)
        self.assertEqual(retrieval.data["session_status"], "valid")
        self.assertEqual(retrieval.data["cookie_version"], 1)
        self.assertEqual(retrieval.data["cookies_json"][0]["name"], "sessionid")

    @override_settings(INSTABOT_WORKER_TOKEN="worker-test-token")
    def test_cookie_version_conflict_is_rejected(self):
        client = APIClient()
        headers = {"HTTP_X_WORKER_TOKEN": "worker-test-token"}
        cookies = [
            {"name": "sessionid", "value": "opaque-value", "domain": ".instagram.com"},
            {"name": "csrftoken", "value": "csrf-value", "domain": ".instagram.com"},
        ]

        first = client.post(
            f"/api/v1/accounts/{self.account.id}/update_cookies/",
            {"cookies": cookies, **self.lock_payload},
            format="json",
            **headers,
        )
        self.assertEqual(first.status_code, 200)

        conflict = client.post(
            f"/api/v1/accounts/{self.account.id}/update_cookies/",
            {"cookies": cookies, "expected_version": 0, **self.lock_payload},
            format="json",
            **headers,
        )
        self.assertEqual(conflict.status_code, 409)

    @override_settings(INSTABOT_WORKER_TOKEN="worker-test-token")
    def test_missing_and_malformed_cookies_get_explicit_states(self):
        client = APIClient()
        headers = {"HTTP_X_WORKER_TOKEN": "worker-test-token"}

        missing_status = client.post(
            f"/api/v1/accounts/{self.account.id}/session_status/",
            {"session_status": "missing", **self.lock_payload},
            format="json",
            **headers,
        )
        self.assertEqual(missing_status.status_code, 200)

        malformed = client.post(
            f"/api/v1/accounts/{self.account.id}/update_cookies/",
            {"cookies": [{"name": "sessionid", "value": "opaque-value", "domain": ".example.com"}], **self.lock_payload},
            format="json",
            **headers,
        )
        self.assertEqual(malformed.status_code, 422)

    @override_settings(INSTABOT_WORKER_TOKEN="worker-test-token")
    def test_worker_cookie_sync_rejects_wrong_lock_owner(self):
        client = APIClient()
        cookies = [
            {"name": "sessionid", "value": "opaque-value", "domain": ".instagram.com"},
            {"name": "csrftoken", "value": "csrf-value", "domain": ".instagram.com"},
        ]
        response = client.post(
            f"/api/v1/accounts/{self.account.id}/update_cookies/",
            {
                "cookies": cookies,
                "job_id": str(self.job.id),
                "lock_owner_token": "wrong-owner-token",
                "execution_generation": self.job.execution_generation,
            },
            format="json",
            HTTP_X_WORKER_TOKEN="worker-test-token",
        )
        self.assertEqual(response.status_code, 409)

    @override_settings(INSTABOT_WORKER_TOKEN="worker-test-token")
    def test_worker_cookie_sync_rejects_missing_owner_evidence(self):
        client = APIClient()
        cookies = [
            {"name": "sessionid", "value": "opaque-value", "domain": ".instagram.com"},
            {"name": "csrftoken", "value": "csrf-value", "domain": ".instagram.com"},
        ]
        response = client.post(
            f"/api/v1/accounts/{self.account.id}/update_cookies/",
            {"cookies": cookies},
            format="json",
            HTTP_X_WORKER_TOKEN="worker-test-token",
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(INSTABOT_WORKER_TOKEN="worker-test-token")
    def test_worker_cookie_sync_rejects_missing_job_id(self):
        client = APIClient()
        response = client.post(
            f"/api/v1/accounts/{self.account.id}/update_cookies/",
            {
                "cookies": [
                    {"name": "sessionid", "value": "opaque-value", "domain": ".instagram.com"},
                    {"name": "csrftoken", "value": "csrf-value", "domain": ".instagram.com"},
                ],
                "lock_owner_token": self.account_lock.owner_token,
            },
            format="json",
            HTTP_X_WORKER_TOKEN="worker-test-token",
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(INSTABOT_WORKER_TOKEN="worker-test-token")
    def test_worker_cookie_and_status_reject_missing_null_malformed_and_stale_generation(self):
        client = APIClient()
        headers = {"HTTP_X_WORKER_TOKEN": "worker-test-token"}
        cookies = [
            {"name": "sessionid", "value": "opaque-value", "domain": ".instagram.com"},
            {"name": "csrftoken", "value": "csrf-value", "domain": ".instagram.com"},
        ]
        for generation in ("missing", None, "0", True, -1, self.job.execution_generation + 1):
            with self.subTest(generation=generation):
                payload = {
                    "cookies": cookies,
                    "job_id": str(self.job.id),
                    "lock_owner_token": self.account_lock.owner_token,
                }
                if generation != "missing":
                    payload["execution_generation"] = generation
                response = client.post(
                    f"/api/v1/accounts/{self.account.id}/update_cookies/",
                    payload,
                    format="json",
                    **headers,
                )
                is_stale = (
                    type(generation) is int
                    and generation >= 0
                    and generation != self.job.execution_generation
                )
                self.assertEqual(response.status_code, 409 if is_stale else 400)

                status_payload = {
                    "session_status": "valid",
                    "job_id": str(self.job.id),
                    "lock_owner_token": self.account_lock.owner_token,
                }
                if generation != "missing":
                    status_payload["execution_generation"] = generation
                status_response = client.post(
                    f"/api/v1/accounts/{self.account.id}/session_status/",
                    status_payload,
                    format="json",
                    **headers,
                )
                self.assertEqual(
                    status_response.status_code,
                    409 if is_stale else 400,
                )

    @override_settings(INSTABOT_WORKER_TOKEN="worker-test-token")
    def test_worker_cookie_sync_rejects_expired_lock(self):
        from api.models import AccountBrowserLock
        lock = AccountBrowserLock.objects.get(account_id=self.account.id)
        lock.expires_at = timezone.now() - timedelta(seconds=1)
        lock.save(update_fields=["expires_at"])

        client = APIClient()
        response = client.post(
            f"/api/v1/accounts/{self.account.id}/update_cookies/",
            {
                "cookies": [
                    {"name": "sessionid", "value": "opaque-value", "domain": ".instagram.com"},
                    {"name": "csrftoken", "value": "csrf-value", "domain": ".instagram.com"},
                ],
                "job_id": str(self.job.id),
                "lock_owner_token": self.account_lock.owner_token,
                "execution_generation": self.job.execution_generation,
            },
            format="json",
            HTTP_X_WORKER_TOKEN="worker-test-token",
        )
        self.assertEqual(response.status_code, 409)
