from types import SimpleNamespace
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from account.models import BotAccount
from .models import AutomationJob


class AutomationJobAPITests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="job-owner",
            password="test-password",
        )
        self.other_user = user_model.objects.create_user(
            username="other-owner",
            password="test-password",
        )
        self.account = BotAccount.objects.create(
            owner=self.user,
            username="automation-account",
            password_encrypted="encrypted-value",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.payload = {
            "account_id": self.account.id,
            "action": "scrape_profile",
            "targets": ["example_user"],
        }

    @patch("api.job_service.execute_automation_job.apply_async")
    def test_submission_queues_once_for_repeated_idempotency_key(self, enqueue):
        enqueue.return_value = SimpleNamespace(id="celery-task-1")
        headers = {"HTTP_IDEMPOTENCY_KEY": "request-1"}

        first = self.client.post("/api/v1/bot/execute/", self.payload, format="json", **headers)
        second = self.client.post("/api/v1/bot/execute/", self.payload, format="json", **headers)

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["job_id"], second.data["job_id"])
        self.assertEqual(enqueue.call_count, 1)
        self.assertEqual(
            AutomationJob.objects.get().status,
            AutomationJob.Status.QUEUED,
        )

    @patch("api.job_service.execute_automation_job.apply_async")
    def test_idempotency_key_cannot_be_reused_for_different_request(self, enqueue):
        enqueue.return_value = SimpleNamespace(id="celery-task-1")
        headers = {"HTTP_IDEMPOTENCY_KEY": "request-2"}
        self.client.post("/api/v1/bot/execute/", self.payload, format="json", **headers)

        changed_payload = {**self.payload, "targets": ["another_user"]}
        response = self.client.post(
            "/api/v1/bot/execute/",
            changed_payload,
            format="json",
            **headers,
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(enqueue.call_count, 1)

    @patch("api.job_service.execute_automation_job.apply_async")
    def test_account_has_at_most_one_active_job(self, enqueue):
        enqueue.return_value = SimpleNamespace(id="celery-task-1")
        self.client.post("/api/v1/bot/execute/", self.payload, format="json")

        response = self.client.post("/api/v1/bot/execute/", self.payload, format="json")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(enqueue.call_count, 1)

    @patch("api.job_service.execute_automation_job.apply_async")
    @patch("celery.current_app.control.revoke")
    def test_queued_job_can_be_cancelled_and_revoked(self, revoke, enqueue):
        enqueue.return_value = SimpleNamespace(id="celery-task-1")
        submission = self.client.post(
            "/api/v1/bot/execute/",
            self.payload,
            format="json",
        )

        response = self.client.post(
            f"/api/v1/bot/jobs/{submission.data['job_id']}/cancel/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], AutomationJob.Status.CANCELLED)
        revoke.assert_called_once_with("celery-task-1", terminate=False)

    def test_running_job_cancellation_is_deferred(self):
        job = AutomationJob.objects.create(
            user=self.user,
            account=self.account,
            action="scrape_profile",
            targets=["example_user"],
            status=AutomationJob.Status.RUNNING,
        )

        response = self.client.post(f"/api/v1/bot/jobs/{job.id}/cancel/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], AutomationJob.Status.CANCELLING)
        self.assertTrue(response.data["cancel_requested"])

    @patch("api.job_service.execute_automation_job.apply_async")
    def test_user_cannot_submit_for_another_users_account(self, enqueue):
        other_account = BotAccount.objects.create(
            owner=self.other_user,
            username="other-account",
            password_encrypted="encrypted-value",
        )
        response = self.client.post(
            "/api/v1/bot/execute/",
            {**self.payload, "account_id": other_account.id},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        enqueue.assert_not_called()

    @patch("api.job_service.execute_automation_job.apply_async")
    def test_user_cannot_read_another_users_job(self, enqueue):
        enqueue.return_value = SimpleNamespace(id="celery-task-1")
        response = self.client.post("/api/v1/bot/execute/", self.payload, format="json")
        other_client = APIClient()
        other_client.force_authenticate(user=self.other_user)

        status_response = other_client.get(
            f"/api/v1/bot/jobs/{response.data['job_id']}/"
        )

        self.assertEqual(status_response.status_code, 404)

    def test_job_submission_requires_authentication(self):
        response = APIClient().post(
            "/api/v1/bot/execute/",
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    @patch("api.job_service.execute_automation_job.apply_async", side_effect=ConnectionError)
    def test_queue_failure_is_reported_and_job_is_marked_failed(self, enqueue):
        response = self.client.post("/api/v1/bot/execute/", self.payload, format="json")

        self.assertEqual(response.status_code, 503)
        job = AutomationJob.objects.get()
        self.assertEqual(job.status, AutomationJob.Status.FAILED)
        self.assertTrue(job.error)
        enqueue.assert_called_once()

    def test_secret_values_are_rejected_from_job_options(self):
        response = self.client.post(
            "/api/v1/bot/execute/",
            {**self.payload, "options": {"instagram_password": "do-not-store"}},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(AutomationJob.objects.exists())

    @patch("api.bot_execute.Redis.from_url")
    def test_owner_can_submit_code_to_pending_verification_job(self, redis_from_url):
        redis_client = redis_from_url.return_value
        redis_client.set.return_value = True
        job = AutomationJob.objects.create(
            user=self.user,
            account=self.account,
            action="like",
            targets=["https://www.instagram.com/p/example/"],
            status=AutomationJob.Status.AWAITING_OTP,
            verification_expires_at=timezone.now() + timedelta(minutes=5),
        )

        response = self.client.post(
            f"/api/v1/bot/jobs/{job.id}/verification/",
            {"code": "123456"},
            format="json",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data, {"status": "received"})
        redis_client.set.assert_called_once()
        self.assertEqual(redis_client.set.call_args.args[1], "123456")
        redis_client.close.assert_called_once()

    @patch("api.bot_execute.Redis.from_url")
    def test_code_submission_is_rejected_for_non_pending_job(self, redis_from_url):
        job = AutomationJob.objects.create(
            user=self.user,
            account=self.account,
            action="like",
            targets=["https://www.instagram.com/p/example/"],
            status=AutomationJob.Status.RUNNING,
        )

        response = self.client.post(
            f"/api/v1/bot/jobs/{job.id}/verification/",
            {"code": "123456"},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        redis_from_url.assert_not_called()

    @patch("api.bot_execute.Redis.from_url")
    def test_expired_verification_job_is_failed_without_delivering_code(
        self,
        redis_from_url,
    ):
        job = AutomationJob.objects.create(
            user=self.user,
            account=self.account,
            action="like",
            targets=["https://www.instagram.com/p/example/"],
            status=AutomationJob.Status.AWAITING_OTP,
            verification_expires_at=timezone.now() - timedelta(seconds=1),
        )

        response = self.client.post(
            f"/api/v1/bot/jobs/{job.id}/verification/",
            {"code": "123456"},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        job.refresh_from_db()
        self.assertEqual(job.status, AutomationJob.Status.FAILED)
        self.assertIsNone(job.verification_expires_at)
        redis_from_url.assert_not_called()

    def test_code_submission_requires_an_authenticatable_numeric_code(self):
        job = AutomationJob.objects.create(
            user=self.user,
            account=self.account,
            action="like",
            targets=["https://www.instagram.com/p/example/"],
            status=AutomationJob.Status.AWAITING_OTP,
            verification_expires_at=timezone.now() + timedelta(minutes=5),
        )

        response = self.client.post(
            f"/api/v1/bot/jobs/{job.id}/verification/",
            {"code": "abc123"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_only_job_owner_can_submit_verification_code(self):
        job = AutomationJob.objects.create(
            user=self.user,
            account=self.account,
            action="like",
            targets=["https://www.instagram.com/p/example/"],
            status=AutomationJob.Status.AWAITING_OTP,
            verification_expires_at=timezone.now() + timedelta(minutes=5),
        )
        other_client = APIClient()
        other_client.force_authenticate(user=self.other_user)

        response = other_client.post(
            f"/api/v1/bot/jobs/{job.id}/verification/",
            {"code": "123456"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
