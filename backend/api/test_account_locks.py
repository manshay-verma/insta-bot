from datetime import timedelta

from django.contrib.auth import get_user_model
from threading import Thread

from django.db import IntegrityError, close_old_connections, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from account.models import BotAccount
from .account_locks import (
    AccountLockBusy,
    AccountLockOwnershipError,
    ExecutionGenerationError,
    acquire_account_lock,
    release_account_lock,
    renew_account_lock,
    resolve_execution_recovery,
    validate_account_lock,
)
from .models import AccountBrowserLock, AutomationJob, ExecutionRecoveryRecord


class AccountBrowserLockTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="lock-owner",
            password="unused",
        )
        self.account = BotAccount.objects.create(
            owner=user,
            username="locked-account",
            password_encrypted="encrypted",
        )
        self.job = AutomationJob.objects.create(
            user=user,
            account=self.account,
            action="scrape_profile",
            targets=["example"],
            status=AutomationJob.Status.RUNNING,
        )

    def test_acquire_validate_renew_and_release(self):
        lock = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=self.job.execution_generation,
        )
        self.assertTrue(
            validate_account_lock(
                account_id=self.account.id,
                job_id=self.job.id,
                owner_token=lock.owner_token,
                execution_generation=self.job.execution_generation,
            )
        )
        renewed = renew_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            owner_token=lock.owner_token,
            execution_generation=self.job.execution_generation,
        )
        self.assertGreater(renewed, timezone.now())
        self.assertTrue(
            release_account_lock(
                account_id=self.account.id,
                job_id=self.job.id,
                owner_token=lock.owner_token,
                execution_generation=self.job.execution_generation,
            )
        )
        self.assertFalse(AccountBrowserLock.objects.filter(account_id=self.account.id).exists())

    def test_second_job_for_same_account_is_busy(self):
        first = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=self.job.execution_generation,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            AutomationJob.objects.create(
                user=self.job.user,
                account=self.account,
                action="follow",
                targets=["example"],
                status=AutomationJob.Status.RUNNING,
            )
        self.assertTrue(
            validate_account_lock(
                account_id=self.account.id,
                job_id=self.job.id,
                owner_token=first.owner_token,
                execution_generation=self.job.execution_generation,
            )
        )

    def test_expired_lock_can_be_reclaimed(self):
        first = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=self.job.execution_generation,
        )
        lock = AccountBrowserLock.objects.get(account_id=self.account.id)
        lock.expires_at = timezone.now() - timedelta(seconds=1)
        lock.save(update_fields=["expires_at"])

        with self.assertRaises(AccountLockBusy):
            acquire_account_lock(
                account_id=self.account.id,
                job_id=self.job.id,
                owner_token=first.owner_token,
                execution_generation=self.job.execution_generation,
            )

    def test_release_requires_matching_owner(self):
        lock = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=self.job.execution_generation,
        )
        with self.assertRaises(AccountLockOwnershipError):
            release_account_lock(
                account_id=self.account.id,
                job_id=self.job.id,
                owner_token="wrong-owner",
                execution_generation=self.job.execution_generation,
            )
        self.assertTrue(AccountBrowserLock.objects.filter(account_id=self.account.id).exists())

    def test_different_accounts_can_be_locked_independently(self):
        other_account = BotAccount.objects.create(
            owner=self.job.user,
            username="other-lock-account",
            password_encrypted="encrypted",
        )
        other_job = AutomationJob.objects.create(
            user=self.job.user,
            account=other_account,
            action="scrape_profile",
            targets=["other"],
            status=AutomationJob.Status.RUNNING,
        )
        first = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=self.job.execution_generation,
        )
        second = acquire_account_lock(
            account_id=other_account.id,
            job_id=other_job.id,
            execution_generation=other_job.execution_generation,
        )
        self.assertNotEqual(first.owner_token, second.owner_token)
        self.assertTrue(
            validate_account_lock(
                account_id=other_account.id,
                job_id=other_job.id,
                owner_token=second.owner_token,
                execution_generation=other_job.execution_generation,
            )
        )

    def test_stale_worker_cannot_renew_or_release_newer_owner(self):
        first = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=self.job.execution_generation,
        )
        AccountBrowserLock.objects.filter(account_id=self.account.id).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.job.status = AutomationJob.Status.SUCCEEDED
        self.job.save(update_fields=["status"])

        second_job = AutomationJob.objects.create(
            user=self.job.user,
            account=self.account,
            action="follow",
            targets=["example"],
            status=AutomationJob.Status.RUNNING,
        )
        with self.assertRaises(AccountLockBusy):
            acquire_account_lock(
                account_id=self.account.id,
                job_id=second_job.id,
                execution_generation=second_job.execution_generation,
            )

        with self.assertRaises(AccountLockOwnershipError):
            renew_account_lock(
                account_id=self.account.id,
                job_id=self.job.id,
                owner_token=first.owner_token,
                execution_generation=self.job.execution_generation,
            )
        self.assertTrue(
            release_account_lock(
                account_id=self.account.id,
                job_id=self.job.id,
                owner_token=first.owner_token,
                execution_generation=self.job.execution_generation,
            )
        )

    def test_stale_completed_job_cannot_acquire_lock(self):
        self.job.status = AutomationJob.Status.SUCCEEDED
        self.job.save(update_fields=["status"])
        with self.assertRaises(AccountLockOwnershipError):
            acquire_account_lock(
                account_id=self.account.id,
                job_id=self.job.id,
                execution_generation=self.job.execution_generation,
            )

    def test_stale_execution_generation_cannot_renew_or_release(self):
        lock = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=0,
        )
        self.job.execution_generation = 1
        self.job.save(update_fields=["execution_generation"])

        with self.assertRaises(AccountLockOwnershipError):
            renew_account_lock(
                account_id=self.account.id,
                job_id=self.job.id,
                owner_token=lock.owner_token,
                execution_generation=0,
            )
        with self.assertRaises(AccountLockOwnershipError):
            validate_account_lock(
                account_id=self.account.id,
                job_id=self.job.id,
                owner_token=lock.owner_token,
                execution_generation=0,
            )
        with self.assertRaises(AccountLockOwnershipError):
            release_account_lock(
                account_id=self.account.id,
                job_id=self.job.id,
                owner_token=lock.owner_token,
                execution_generation=0,
            )

    def test_execution_generation_mismatch_cannot_acquire(self):
        with self.assertRaises(ExecutionGenerationError):
            acquire_account_lock(
                account_id=self.account.id,
                job_id=self.job.id,
                execution_generation=99,
            )

    def test_atomic_recovery_is_idempotent_for_duplicate_delivery(self):
        self.job.status = AutomationJob.Status.QUEUED
        self.job.save(update_fields=["status"])
        first = resolve_execution_recovery(
            job_id=self.job.id,
            source="initial",
            delivery_key="initial:test-key",
        )
        second = resolve_execution_recovery(
            job_id=self.job.id,
            source="initial",
            delivery_key="initial:test-key",
        )
        self.job.refresh_from_db()
        self.assertEqual(first.action, "start_new_generation")
        self.assertEqual(second.action, "duplicate_delivery")
        self.assertEqual(first.execution_generation, 1)
        self.assertEqual(second.execution_generation, 1)
        self.assertEqual(self.job.execution_generation, 1)
        self.assertEqual(self.job.attempt_count, 1)

    def test_crash_after_allocation_resumes_same_generation(self):
        self.job.status = AutomationJob.Status.QUEUED
        self.job.save(update_fields=["status"])
        prepared = resolve_execution_recovery(
            job_id=self.job.id,
            source="initial",
            delivery_key="initial:crash-key",
        )
        resumed = resolve_execution_recovery(
            job_id=self.job.id,
            source="initial",
            delivery_key="initial:crash-key",
            recovery_resume=True,
            runner_identity_confirmed=True,
        )
        self.job.refresh_from_db()
        self.assertEqual(prepared.execution_generation, 1)
        self.assertEqual(resumed.action, "resume_prepared_generation")
        self.assertEqual(resumed.execution_generation, 1)
        self.assertEqual(self.job.execution_generation, 1)

    def test_transaction_rollback_does_not_persist_generation(self):
        self.job.status = AutomationJob.Status.QUEUED
        self.job.save(update_fields=["status"])
        try:
            with transaction.atomic():
                resolve_execution_recovery(
                    job_id=self.job.id,
                    source="initial",
                    delivery_key="initial:rollback-key",
                )
                raise RuntimeError("simulate crash after allocation commit boundary")
        except RuntimeError:
            pass
        self.job.refresh_from_db()
        self.assertEqual(self.job.execution_generation, 0)
        self.assertIsNone(self.job.recovery_delivery_key)
        self.assertEqual(self.job.attempt_count, 0)

    def test_application_retry_counter_is_separate_and_idempotent(self):
        self.job.status = AutomationJob.Status.QUEUED
        self.job.save(update_fields=["status"])
        first = resolve_execution_recovery(
            job_id=self.job.id,
            source="initial",
            delivery_key="initial:base-key",
        )
        retry = resolve_execution_recovery(
            job_id=self.job.id,
            source="application_retry",
            delivery_key="application:test-job:2",
        )
        duplicate = resolve_execution_recovery(
            job_id=self.job.id,
            source="application_retry",
            delivery_key="application:test-job:2",
        )
        self.job.refresh_from_db()
        self.assertEqual(first.execution_generation, 1)
        self.assertEqual(retry.execution_generation, 2)
        self.assertEqual(duplicate.action, "duplicate_delivery")
        self.assertEqual(self.job.application_retry_count, 1)
        self.assertEqual(self.job.worker_redelivery_count, 0)

    def test_duplicate_worker_loss_delivery_allocates_and_counts_once(self):
        self.job.status = AutomationJob.Status.RUNNING
        self.job.save(update_fields=["status"])
        lock = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=0,
        )

        first = resolve_execution_recovery(
            job_id=self.job.id,
            source="worker_redelivery",
            delivery_key="caller-must-not-use-this-key",
            supplied_generation=0,
            owner_token=lock.owner_token,
            runner_identity_confirmed=True,
        )
        second = resolve_execution_recovery(
            job_id=self.job.id,
            source="worker_redelivery",
            delivery_key="caller-must-not-use-this-key",
            supplied_generation=0,
            owner_token=lock.owner_token,
            runner_identity_confirmed=True,
        )
        third = resolve_execution_recovery(
            job_id=self.job.id,
            source="worker_redelivery",
            delivery_key="caller-must-not-use-this-key",
            supplied_generation=0,
            owner_token=lock.owner_token,
            runner_identity_confirmed=True,
        )

        self.job.refresh_from_db()
        self.assertEqual(first.action, "start_new_generation")
        self.assertEqual(second.action, "duplicate_delivery")
        self.assertEqual(third.action, "duplicate_delivery")
        self.assertEqual(first.execution_generation, 1)
        self.assertEqual(self.job.execution_generation, 1)
        self.assertEqual(self.job.worker_redelivery_count, 1)
        self.assertEqual(self.job.attempt_count, 1)
        self.assertEqual(
            ExecutionRecoveryRecord.objects.filter(
                job=self.job,
                failed_generation=0,
                recovery_kind="worker_redelivery",
                allocated_generation=1,
            ).count(),
            1,
        )

    def test_worker_loss_recovery_history_survives_current_key_overwrite(self):
        self.job.status = AutomationJob.Status.RUNNING
        self.job.save(update_fields=["status"])
        lock = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=0,
        )
        worker_result = resolve_execution_recovery(
            job_id=self.job.id,
            source="worker_redelivery",
            supplied_generation=0,
            owner_token=lock.owner_token,
            runner_identity_confirmed=True,
        )
        application_result = resolve_execution_recovery(
            job_id=self.job.id,
            source="application_retry",
            delivery_key=f"application:{self.job.id}:2",
            supplied_generation=worker_result.execution_generation,
        )

        duplicate = resolve_execution_recovery(
            job_id=self.job.id,
            source="worker_redelivery",
            supplied_generation=0,
            owner_token=lock.owner_token,
            runner_identity_confirmed=True,
        )

        self.job.refresh_from_db()
        self.assertEqual(application_result.execution_generation, 2)
        self.assertEqual(duplicate.action, "duplicate_delivery")
        self.assertEqual(duplicate.execution_generation, 1)
        self.assertEqual(self.job.execution_generation, 2)
        self.assertEqual(self.job.worker_redelivery_count, 1)
        self.assertEqual(self.job.application_retry_count, 1)
        self.assertTrue(
            ExecutionRecoveryRecord.objects.filter(
                job=self.job,
                failed_generation=0,
                recovery_kind="worker_redelivery",
                allocated_generation=1,
            ).exists()
        )

    def test_unexpired_otp_never_allocates_replacement_generation(self):
        self.job.status = AutomationJob.Status.AWAITING_OTP
        self.job.execution_generation = 3
        self.job.verification_expires_at = timezone.now() + timedelta(minutes=1)
        self.job.save(
            update_fields=[
                "status",
                "execution_generation",
                "verification_expires_at",
            ]
        )
        lock = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=3,
        )
        decision = resolve_execution_recovery(
            job_id=self.job.id,
            source="worker_redelivery",
            supplied_generation=3,
            owner_token=lock.owner_token,
            runner_identity_confirmed=True,
        )
        self.job.refresh_from_db()
        self.assertEqual(decision.action, "otp_reconnect")
        self.assertEqual(decision.execution_generation, 3)
        self.assertEqual(self.job.execution_generation, 3)
        self.assertEqual(self.job.worker_redelivery_count, 0)

    def test_unconfirmed_runner_cannot_reconnect_unexpired_otp(self):
        self.job.status = AutomationJob.Status.AWAITING_OTP
        self.job.execution_generation = 3
        self.job.verification_expires_at = timezone.now() + timedelta(minutes=1)
        self.job.save(
            update_fields=[
                "status",
                "execution_generation",
                "verification_expires_at",
            ]
        )
        lock = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=3,
        )
        with self.assertRaises(AccountLockOwnershipError):
            resolve_execution_recovery(
                job_id=self.job.id,
                source="worker_redelivery",
                supplied_generation=3,
                owner_token=lock.owner_token,
                runner_identity_confirmed=False,
            )
        self.job.refresh_from_db()
        persisted_lock = AccountBrowserLock.objects.get(account=self.account)
        self.assertEqual(self.job.execution_generation, 3)
        self.assertTrue(persisted_lock.pk is not None)

    def test_worker_loss_without_confirmed_identity_fails_closed(self):
        self.job.status = AutomationJob.Status.QUEUED
        self.job.save(update_fields=["status"])
        with self.assertRaises(AccountLockOwnershipError):
            resolve_execution_recovery(
                job_id=self.job.id,
                source="worker_redelivery",
                delivery_key="worker-loss:test-key",
                runner_identity_confirmed=False,
            )
        self.job.refresh_from_db()
        self.assertEqual(self.job.execution_generation, 0)

    def test_wrong_missing_or_stale_runner_identity_does_not_mutate_lock(self):
        self.job.status = AutomationJob.Status.RUNNING
        self.job.save(update_fields=["status"])
        lock = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=0,
        )

        for owner_token, stale_generation in (
            ("wrong-owner-token", 0),
            (None, 0),
            (lock.owner_token, 99),
        ):
            with self.subTest(owner_token=bool(owner_token), stale_generation=stale_generation):
                with self.assertRaises(AccountLockOwnershipError):
                    resolve_execution_recovery(
                        job_id=self.job.id,
                        source="worker_redelivery",
                        supplied_generation=stale_generation,
                        owner_token=owner_token,
                        runner_identity_confirmed=True,
                    )
                self.job.refresh_from_db()
                persisted_lock = AccountBrowserLock.objects.get(account=self.account)
                self.assertEqual(self.job.execution_generation, 0)
                self.assertEqual(self.job.worker_redelivery_count, 0)
                self.assertEqual(persisted_lock.execution_generation, 0)
                self.assertTrue(
                    AccountBrowserLock.objects.filter(
                        account_id=self.account.id,
                        job_id=self.job.id,
                        execution_generation=0,
                    ).exists()
                )

    def test_worker_loss_limit_is_persistent_and_atomic(self):
        self.job.status = AutomationJob.Status.RUNNING
        self.job.worker_redelivery_count = 2
        self.job.save(
            update_fields=["status", "worker_redelivery_count"],
        )
        lock = acquire_account_lock(
            account_id=self.account.id,
            job_id=self.job.id,
            execution_generation=0,
        )
        decision = resolve_execution_recovery(
            job_id=self.job.id,
            source="worker_redelivery",
            delivery_key="worker-loss:limit-key",
            supplied_generation=0,
            owner_token=lock.owner_token,
            runner_identity_confirmed=True,
        )
        self.job.refresh_from_db()
        self.assertEqual(decision.action, "worker_loss_limit")
        self.assertEqual(self.job.execution_generation, 0)
        self.assertEqual(self.job.recovery_state, "worker_loss_limit")

    def test_malformed_execution_generation_is_rejected_by_lock_primitives(self):
        for malformed in (None, "0", 0.0, True, -1):
            with self.subTest(malformed=malformed):
                with self.assertRaises(ExecutionGenerationError):
                    acquire_account_lock(
                        account_id=self.account.id,
                        job_id=self.job.id,
                        execution_generation=malformed,
                    )


class ConcurrentExecutionRecoveryTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        user = get_user_model().objects.create_user(
            username="concurrent-recovery-owner",
            password="test-password",
        )
        self.account = BotAccount.objects.create(
            owner=user,
            username="concurrent-recovery-account",
            password_encrypted="encrypted",
        )
        self.job = AutomationJob.objects.create(
            user=user,
            account=self.account,
            action="scrape_profile",
            targets=["example"],
            status=AutomationJob.Status.QUEUED,
        )

    def test_concurrent_same_delivery_allocates_one_generation(self):
        barrier = __import__("threading").Barrier(2)
        results = []
        errors = []

        def deliver():
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                decision = resolve_execution_recovery(
                    job_id=self.job.id,
                    source="initial",
                    delivery_key="initial:concurrent-key",
                )
                results.append(decision.action)
            except BaseException as exc:
                errors.append(exc)
            finally:
                close_old_connections()

        threads = [Thread(target=deliver), Thread(target=deliver)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.job.refresh_from_db()
        self.assertEqual(errors, [])
        self.assertEqual(sorted(results).count("start_new_generation"), 1)
        self.assertEqual(sorted(results).count("duplicate_delivery"), 1)
        self.assertEqual(self.job.execution_generation, 1)
        self.assertEqual(self.job.attempt_count, 1)
