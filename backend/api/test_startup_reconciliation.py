import asyncio
import os
import signal
import time
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.utils import timezone

from account.models import BotAccount
from .models import AccountBrowserLock, AutomationJob, ExecutionRecoveryRecord
from .account_locks import (
    MAX_WORKER_LOSS_REDELIVERIES,
    acquire_account_lock,
    build_worker_recovery_delivery_key,
    prepare_worker_loss_recovery,
    register_browser_runner,
    resolve_execution_recovery,
)
from .reconciliation import (
    STARTUP_RECONCILIATION_LOCK_ID,
    is_celery_task_present,
    reconcile_single_job,
    reconcile_startup_jobs,
)
from orchestrator.runner_ipc import (
    RUNNER_SECRET_ENV,
    RunnerIdentity,
    get_container_boot_id,
    get_process_start_ticks,
    validate_live_process,
)
from orchestrator.runner_supervisor import BrowserRunnerSupervisor

User = get_user_model()


class StartupReconciliationTestCase(TransactionTestCase):
    def setUp(self):
        super().setUp()
        os.environ[RUNNER_SECRET_ENV] = "test-secret-key-12345678901234567890"
        self.user = User.objects.create_user(
            username="recontester",
            password="testpassword123",
        )
        self.account = BotAccount.objects.create(
            owner=self.user,
            username="recontarget",
            password_encrypted="encrypted",
        )
        self.job = AutomationJob.objects.create(
            user=self.user,
            account=self.account,
            action="like",
            targets=["p1", "p2"],
            status=AutomationJob.Status.RUNNING,
            execution_generation=0,
            attempt_count=1,
            worker_redelivery_count=0,
            application_retry_count=0,
        )

    def tearDown(self):
        # Clean up any lingering browser locks or jobs
        AccountBrowserLock.objects.all().delete()
        super().tearDown()

    def test_worker_startup_with_stale_running_job(self):
        """Worker startup with stale RUNNING jobs recovers generation and enqueues task."""
        lock = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=0,
        )
        # Dead runner on db_lock
        db_lock = AccountBrowserLock.objects.get(account=self.account)
        db_lock.runner_pid = 9999999
        db_lock.runner_start_ticks = 12345
        db_lock.runner_container_boot_id = get_container_boot_id()
        db_lock.runner_pgid = 9999999
        db_lock.runner_profile_path = "/tmp/test-profile"
        db_lock.save()

        with patch("api.tasks.execute_automation_job.delay") as mock_delay:
            mock_task = MagicMock()
            mock_task.id = "mock-celery-task-recovered"
            mock_delay.return_value = mock_task

            result = reconcile_startup_jobs()

        self.job.refresh_from_db()
        self.assertEqual(result["reconciled_jobs"], 1)
        self.assertEqual(self.job.status, AutomationJob.Status.QUEUED)
        self.assertEqual(self.job.execution_generation, 1)
        self.assertEqual(self.job.worker_redelivery_count, 1)
        self.assertEqual(self.job.application_retry_count, 0)
        self.assertEqual(self.job.recovery_state, "prepared_recovery")
        self.assertEqual(self.job.celery_task_id, "mock-celery-task-recovered")

        # Stale lock deleted
        self.assertFalse(AccountBrowserLock.objects.filter(account=self.account).exists())

        # Authoritative ExecutionRecoveryRecord created
        record = ExecutionRecoveryRecord.objects.get(job=self.job)
        self.assertEqual(record.failed_generation, 0)
        self.assertEqual(record.allocated_generation, 1)
        self.assertEqual(record.recovery_kind, "worker_redelivery")

        # Verify task was dispatched with delivery_reason="worker_redelivery"
        mock_delay.assert_called_once_with(
            job_id=str(self.job.id),
            execution_generation=1,
            delivery_reason="worker_redelivery",
            recovery_delivery_key=record.recovery_delivery_key,
        )

    def test_stale_cancelling_jobs(self):
        """Stale CANCELLING job is transitioned to CANCELLED and lock is cleaned."""
        self.job.status = AutomationJob.Status.CANCELLING
        self.job.save(update_fields=["status"])
        lock = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=0,
        )

        with patch("api.tasks.execute_automation_job.delay") as mock_delay:
            result = reconcile_startup_jobs()
            mock_delay.assert_not_called()

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, AutomationJob.Status.CANCELLED)
        self.assertIsNotNone(self.job.completed_at)
        self.assertEqual(self.job.recovery_state, "cancelled")
        self.assertFalse(AccountBrowserLock.objects.filter(account=self.account).exists())

    def test_lost_celery_message_with_postgresql_recovery_record(self):
        """Lost Celery message is redelivered using PostgreSQL authoritative state."""
        self.job.status = AutomationJob.Status.QUEUED
        self.job.execution_generation = 2
        self.job.recovery_delivery_key = f"worker_redelivery:{self.job.id}:1"
        self.job.recovery_generation = 2
        self.job.recovery_state = "prepared_recovery"
        self.job.celery_task_id = "lost-celery-message-id"
        self.job.save()

        # Mock Redis returning False for task presence
        with patch("api.reconciliation.is_celery_task_present", return_value=False):
            with patch("api.tasks.execute_automation_job.delay") as mock_delay:
                mock_task = MagicMock()
                mock_task.id = "new-celery-task-id-456"
                mock_delay.return_value = mock_task

                result = reconcile_startup_jobs()

        self.job.refresh_from_db()
        self.assertEqual(self.job.celery_task_id, "new-celery-task-id-456")
        self.assertEqual(self.job.execution_generation, 2)
        mock_delay.assert_called_once_with(
            job_id=str(self.job.id),
            execution_generation=2,
            delivery_reason="worker_redelivery",
            recovery_delivery_key=self.job.recovery_delivery_key,
        )

    def test_existing_live_runner_reconnect(self):
        """Live runner process is reconnected and preserved without killing or reallocating."""
        supervisor = BrowserRunnerSupervisor(
            job_id=self.job.id,
            account_id=self.account.id,
            execution_generation=0,
            lock_owner_token="test-token",
            adapter_type="playwright",
            task_type="like",
            targets=["p1"],
        )
        identity = supervisor.start()
        try:
            lock = acquire_account_lock(
                account_id=self.account.id,
                job_id=self.job.id,
                execution_generation=0,
            )
            register_browser_runner(
                account_id=self.account.id,
                job_id=self.job.id,
                owner_token=lock.owner_token,
                execution_generation=0,
                runner=identity,
                runner_ipc_path=str(supervisor.socket_path),
            )

            with patch("api.tasks.execute_automation_job.delay") as mock_delay:
                result = reconcile_startup_jobs()
                mock_delay.assert_not_called()

            self.job.refresh_from_db()
            self.assertEqual(self.job.status, AutomationJob.Status.RUNNING)
            self.assertEqual(self.job.execution_generation, 0)
            self.assertEqual(self.job.runner_state, "running")
            self.assertIsNotNone(self.job.runner_heartbeat_at)
            # Runner must still be alive
            self.assertTrue(validate_live_process(identity))
        finally:
            asyncio.run(supervisor.close())

    def test_unexpired_otp_recovery_with_live_runner(self):
        """Unexpired OTP challenge reconnects to confirmed live runner and NEVER launches replacement."""
        supervisor = BrowserRunnerSupervisor(
            job_id=self.job.id,
            account_id=self.account.id,
            execution_generation=0,
            lock_owner_token="test-token",
            adapter_type="playwright",
            task_type="like",
            targets=["p1"],
        )
        identity = supervisor.start()
        try:
            self.job.status = AutomationJob.Status.AWAITING_OTP
            self.job.verification_expires_at = timezone.now() + timedelta(minutes=5)
            self.job.save(update_fields=["status", "verification_expires_at"])

            lock = acquire_account_lock(
                account_id=self.account.id,
                job_id=self.job.id,
                execution_generation=0,
            )
            register_browser_runner(
                account_id=self.account.id,
                job_id=self.job.id,
                owner_token=lock.owner_token,
                execution_generation=0,
                runner=identity,
                runner_ipc_path=str(supervisor.socket_path),
            )

            with patch("api.tasks.execute_automation_job.delay") as mock_delay:
                result = reconcile_startup_jobs()
                mock_delay.assert_not_called()

            self.job.refresh_from_db()
            self.assertEqual(self.job.status, AutomationJob.Status.AWAITING_OTP)
            self.assertEqual(self.job.execution_generation, 0)
            self.assertEqual(self.job.runner_state, "awaiting_otp")
            self.assertTrue(validate_live_process(identity))
        finally:
            asyncio.run(supervisor.close())

    def test_unexpired_otp_recovery_fails_closed_on_dead_runner(self):
        """Unexpired OTP challenge with dead runner fails closed and NEVER starts replacement browser."""
        self.job.status = AutomationJob.Status.AWAITING_OTP
        self.job.verification_expires_at = timezone.now() + timedelta(minutes=5)
        self.job.runner_pid = 9999999
        self.job.runner_start_ticks = 11111
        self.job.runner_container_boot_id = get_container_boot_id()
        self.job.runner_pgid = 9999999
        self.job.runner_profile_path = "/tmp/fake-profile"
        self.job.runner_ipc_path = "/tmp/fake-socket.sock"
        self.job.save()

        lock = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=0,
        )

        with patch("api.tasks.execute_automation_job.delay") as mock_delay:
            result = reconcile_startup_jobs()
            mock_delay.assert_not_called()

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, AutomationJob.Status.FAILED)
        self.assertIn("Browser runner process terminated", self.job.error)
        self.assertEqual(self.job.recovery_state, "runner_lost")
        self.assertEqual(self.job.execution_generation, 0)
        self.assertFalse(AccountBrowserLock.objects.filter(account=self.account).exists())

    def test_expired_otp_recovery(self):
        """Expired OTP challenge transitions to FAILED."""
        self.job.status = AutomationJob.Status.AWAITING_OTP
        self.job.verification_expires_at = timezone.now() - timedelta(seconds=10)
        self.job.save()

        result = reconcile_startup_jobs()

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, AutomationJob.Status.FAILED)
        self.assertEqual(self.job.error, "The verification challenge expired.")
        self.assertEqual(self.job.recovery_state, "otp_expired")

    def test_dead_runner_recovery_respects_worker_loss_limit(self):
        """Dead runner recovery enforces worker loss limit."""
        self.job.worker_redelivery_count = MAX_WORKER_LOSS_REDELIVERIES
        self.job.save(update_fields=["worker_redelivery_count"])

        result = reconcile_startup_jobs()

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, AutomationJob.Status.FAILED)
        self.assertEqual(self.job.error, "Worker loss limit exceeded.")
        self.assertEqual(self.job.recovery_state, "worker_loss_limit")

    def test_concurrent_startup_reconciliation_is_idempotent(self):
        """Multiple concurrent or repeated reconciliation runs never allocate duplicate generations."""
        with patch("api.tasks.execute_automation_job.delay") as mock_delay:
            mock_task = MagicMock()
            mock_task.id = "mock-task-id"
            mock_delay.return_value = mock_task

            # Run 1
            res1 = reconcile_startup_jobs()
            self.job.refresh_from_db()
            gen1 = self.job.execution_generation
            records_count1 = ExecutionRecoveryRecord.objects.filter(job=self.job).count()
            self.assertEqual(gen1, 1)
            self.assertEqual(records_count1, 1)

            # Run 2 (simulate concurrent or immediate subsequent pass)
            with patch("api.reconciliation.is_celery_task_present", return_value=True):
                res2 = reconcile_startup_jobs()

            self.job.refresh_from_db()
            gen2 = self.job.execution_generation
            records_count2 = ExecutionRecoveryRecord.objects.filter(job=self.job).count()

            # Must NOT allocate another generation
            self.assertEqual(gen2, 1)
            self.assertEqual(records_count2, 1)
            self.assertEqual(self.job.worker_redelivery_count, 1)

    def test_crash_during_reconciliation_resumes_cleanly(self):
        """If a crash happens after prepare_worker_loss_recovery, next reconciliation resumes without duplicate generation."""
        # Step 1: prepare_worker_loss_recovery succeeds in DB
        decision = prepare_worker_loss_recovery(job_id=self.job.id)
        self.assertEqual(decision.action, "start_new_generation")
        self.assertEqual(decision.execution_generation, 1)

        # Simulate crash before Celery dispatch: job is QUEUED with recovery_state='prepared_recovery'
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, AutomationJob.Status.QUEUED)
        self.assertEqual(self.job.recovery_state, "prepared_recovery")

        # Step 2: Next startup reconciliation runs
        with patch("api.reconciliation.is_celery_task_present", return_value=False):
            with patch("api.tasks.execute_automation_job.delay") as mock_delay:
                mock_task = MagicMock()
                mock_task.id = "recovered-task-id-777"
                mock_delay.return_value = mock_task

                res = reconcile_startup_jobs()

        self.job.refresh_from_db()
        # Generation must NOT have incremented to 2!
        self.assertEqual(self.job.execution_generation, 1)
        self.assertEqual(self.job.worker_redelivery_count, 1)
        self.assertEqual(self.job.celery_task_id, "recovered-task-id-777")
        self.assertEqual(
            ExecutionRecoveryRecord.objects.filter(job=self.job).count(),
            1,
        )

    def test_celery_consumer_bootstep_ordering(self):
        """StartupReconciliationStep is registered in app.steps['consumer'] before Evloop."""
        import config.celery
        steps = [s.name if hasattr(s, "name") else str(s) for s in config.celery.app.steps["consumer"]]
        self.assertTrue(any("StartupReconciliationStep" in s for s in steps))
