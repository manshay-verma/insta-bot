import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from account.models import BotAccount
from .models import AccountBrowserLock, AutomationJob, ExecutionRecoveryRecord
from .logging import log_structured

logger = logging.getLogger(__name__)


LOCK_TTL_SECONDS = 30 * 60
MAX_WORKER_LOSS_REDELIVERIES = 2


def build_worker_recovery_delivery_key(*, job_id, failed_generation):
    return (
        f"worker_redelivery:{job_id}:{normalize_execution_generation(failed_generation)}"
    )


class AccountLockError(Exception):
    pass


class AccountLockBusy(AccountLockError):
    pass


class AccountLockOwnershipError(AccountLockError):
    pass


@dataclass(frozen=True)
class AccountLock:
    owner_token: str
    expires_at: object
    execution_generation: int = 0


def hash_owner_token(owner_token: str) -> str:
    return hashlib.sha256(owner_token.encode("utf-8")).hexdigest()


class ExecutionGenerationError(AccountLockError):
    pass


def normalize_execution_generation(value):
    if type(value) is not int:
        raise ExecutionGenerationError(
            "execution_generation must be a non-negative integer."
        )
    if value < 0:
        raise ExecutionGenerationError(
            "execution_generation must be a non-negative integer."
        )
    return value


@transaction.atomic
def allocate_execution_generation(
    *,
    job_id,
    reason,
):
    """Atomically allocate one new browser execution generation."""
    source = (
        "application_retry"
        if reason == "application_retry"
        else "initial"
    )
    if reason == "worker_redelivery":
        raise ExecutionGenerationError(
            "Worker-loss recovery requires resolve_execution_recovery with confirmed identity."
        )
    return resolve_execution_recovery(
        job_id=job_id,
        source=source,
        runner_identity_confirmed=reason == "worker_redelivery",
    ).execution_generation


@dataclass(frozen=True)
class ExecutionRecoveryDecision:
    action: str
    execution_generation: int
    delivery_key: str
    worker_redelivery_count: int
    application_retry_count: int


def _normalize_delivery_key(delivery_key, *, job_id):
    if delivery_key is None:
        return None
    if not isinstance(delivery_key, str) or not delivery_key.strip():
        raise ExecutionGenerationError("delivery_key must be a non-empty string.")
    if len(delivery_key) > 128:
        raise ExecutionGenerationError("delivery_key exceeds 128 characters.")
    return delivery_key


@transaction.atomic
def resolve_execution_recovery(
    *,
    job_id,
    source,
    delivery_key=None,
    supplied_generation=None,
    owner_token=None,
    recovery_resume=False,
    runner_identity_confirmed=False,
):
    """
    PostgreSQL authority for generation allocation and duplicate recovery decisions.

    Allocation, counter mutation, and idempotency records are committed together.
    A caller claiming worker loss or crash recovery must provide confirmed process
    identity evidence; otherwise this function fails closed.
    """
    job = AutomationJob.objects.select_for_update().get(id=job_id)
    delivery_key = _normalize_delivery_key(delivery_key, job_id=job_id)

    failed_generation = None
    if source == "worker_redelivery":
        if supplied_generation is not None:
            supplied_generation = normalize_execution_generation(supplied_generation)
            # Reconciliation publishes the allocated generation. A prepared
            # record is keyed by the failed generation, so map the published
            # generation back before rebuilding its delivery key.
            prepared_record = (
                ExecutionRecoveryRecord.objects.filter(
                    job_id=job.id,
                    allocated_generation=supplied_generation,
                    recovery_kind="worker_redelivery",
                )
                .order_by("created_at")
                .first()
            )
            if (
                prepared_record is not None
                and prepared_record.failed_generation != supplied_generation
            ):
                failed_generation = prepared_record.failed_generation
            else:
                failed_generation = supplied_generation
        else:
            failed_generation = job.execution_generation
        delivery_key = build_worker_recovery_delivery_key(
            job_id=job.id,
            failed_generation=failed_generation,
        )
    elif supplied_generation is not None and source not in {"application_retry", "worker_redelivery"}:
        supplied_generation = normalize_execution_generation(supplied_generation)
        if supplied_generation != job.execution_generation:
            raise ExecutionGenerationError(
                "The requested execution generation is stale."
            )

    if owner_token is not None or (
        source == "worker_redelivery" and job.recovery_state != "prepared_recovery"
    ):
        if owner_token is None:
            raise AccountLockOwnershipError(
                "A confirmed runner lock owner token is required."
            )
        lock = (
            AccountBrowserLock.objects.select_for_update()
            .select_related("job")
            .filter(account_id=job.account_id, job_id=job.id)
            .first()
        )
        if (
            lock is None
            or not hmac.compare_digest(lock.owner_token_hash, hash_owner_token(owner_token))
            or lock.expires_at <= timezone.now()
        ):
            raise AccountLockOwnershipError(
                "The account process identity is ambiguous or stale."
            )
        if source == "worker_redelivery":
            recovery_record_exists = ExecutionRecoveryRecord.objects.filter(
                job_id=job.id,
                failed_generation=failed_generation,
                recovery_kind="worker_redelivery",
            ).exists()
            if (
                lock.execution_generation != failed_generation
                and not (
                    lock.execution_generation == job.execution_generation
                    and recovery_record_exists
                )
            ):
                raise AccountLockOwnershipError(
                    "The worker-loss runner generation is ambiguous or stale."
                )
        elif (
            lock.execution_generation != job.execution_generation
            or lock.job.execution_generation != job.execution_generation
        ):
            raise AccountLockOwnershipError(
                "The account process identity is ambiguous or stale."
            )

    if job.status in {
        AutomationJob.Status.SUCCEEDED,
        AutomationJob.Status.FAILED,
        AutomationJob.Status.CANCELLED,
    }:
        raise ExecutionGenerationError("A terminal job cannot start a new execution.")

    if job.cancel_requested:
        job.status = AutomationJob.Status.CANCELLED
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "completed_at", "updated_at"])
        raise ExecutionGenerationError("The job was cancelled.")

    now = timezone.now()
    if (
        job.status == AutomationJob.Status.AWAITING_OTP
        and job.verification_expires_at is not None
        and job.verification_expires_at > now
    ):
        if not runner_identity_confirmed:
            raise AccountLockOwnershipError(
                "Confirmed existing runner identity is required for OTP recovery."
            )
        return ExecutionRecoveryDecision(
            action="otp_reconnect",
            execution_generation=job.execution_generation,
            delivery_key=delivery_key or "",
            worker_redelivery_count=job.worker_redelivery_count,
            application_retry_count=job.application_retry_count,
        )
    if (
        job.status == AutomationJob.Status.AWAITING_OTP
        and (
            job.verification_expires_at is None
            or job.verification_expires_at <= now
        )
    ):
        job.status = AutomationJob.Status.FAILED
        job.error = "The verification challenge expired."
        job.completed_at = now
        job.verification_expires_at = None
        job.save(
            update_fields=[
                "status",
                "error",
                "completed_at",
                "verification_expires_at",
                "updated_at",
            ]
        )
        raise ExecutionGenerationError("The verification challenge expired.")

    if source in {"worker_redelivery", "prepared_recovery"}:
        recovery_record = (
            ExecutionRecoveryRecord.objects.select_for_update()
            .filter(
                job_id=job.id,
                failed_generation=failed_generation,
                recovery_kind="worker_redelivery",
            )
            .first()
        )
        if recovery_record is not None:
            if recovery_record.recovery_delivery_key != delivery_key:
                raise ExecutionGenerationError(
                    "The worker-loss recovery record is inconsistent."
                )
            if recovery_resume:
                if not runner_identity_confirmed:
                    raise AccountLockOwnershipError(
                        "Runner identity must be confirmed before crash recovery."
                    )
                return ExecutionRecoveryDecision(
                    action="resume_prepared_generation",
                    execution_generation=recovery_record.allocated_generation,
                    delivery_key=delivery_key,
                    worker_redelivery_count=job.worker_redelivery_count,
                    application_retry_count=job.application_retry_count,
                )
            if (
                job.status == AutomationJob.Status.QUEUED
                and job.recovery_state == "prepared_recovery"
            ):
                job.status = AutomationJob.Status.RUNNING
                job.recovery_state = "executing"
                job.started_at = job.started_at or now
                job.attempt_count += 1
                job.save(
                    update_fields=[
                        "status",
                        "recovery_state",
                        "started_at",
                        "attempt_count",
                        "updated_at",
                    ]
                )
                return ExecutionRecoveryDecision(
                    action="start_prepared_generation",
                    execution_generation=recovery_record.allocated_generation,
                    delivery_key=delivery_key,
                    worker_redelivery_count=job.worker_redelivery_count,
                    application_retry_count=job.application_retry_count,
                )
            return ExecutionRecoveryDecision(
                action="duplicate_delivery",
                execution_generation=recovery_record.allocated_generation,
                delivery_key=delivery_key,
                worker_redelivery_count=job.worker_redelivery_count,
                application_retry_count=job.application_retry_count,
            )

    if delivery_key and getattr(job, "recovery_delivery_key", None) == delivery_key:
        if getattr(job, "recovery_generation", job.execution_generation) != job.execution_generation:
            raise ExecutionGenerationError(
                "The recovery delivery record is inconsistent with the current generation."
            )
        if recovery_resume:
            if not runner_identity_confirmed:
                raise AccountLockOwnershipError(
                    "Runner identity must be confirmed before crash recovery."
                )
            return ExecutionRecoveryDecision(
                action="resume_prepared_generation",
                execution_generation=job.execution_generation,
                delivery_key=delivery_key,
                worker_redelivery_count=job.worker_redelivery_count,
                application_retry_count=job.application_retry_count,
            )
        if (
            job.status == AutomationJob.Status.QUEUED
            and job.recovery_state == "prepared_recovery"
        ):
            job.status = AutomationJob.Status.RUNNING
            job.recovery_state = "executing"
            job.started_at = job.started_at or now
            job.attempt_count += 1
            job.save(
                update_fields=[
                    "status",
                    "recovery_state",
                    "started_at",
                    "attempt_count",
                    "updated_at",
                ]
            )
            return ExecutionRecoveryDecision(
                action="start_prepared_generation",
                execution_generation=job.execution_generation,
                delivery_key=delivery_key,
                worker_redelivery_count=job.worker_redelivery_count,
                application_retry_count=job.application_retry_count,
            )
        return ExecutionRecoveryDecision(
            action="duplicate_delivery",
            execution_generation=job.execution_generation,
            delivery_key=delivery_key,
            worker_redelivery_count=job.worker_redelivery_count,
            application_retry_count=job.application_retry_count,
        )

    if (
        source == "initial"
        and supplied_generation is not None
        and supplied_generation == job.execution_generation
    ):
        return ExecutionRecoveryDecision(
            action="duplicate_delivery",
            execution_generation=job.execution_generation,
            delivery_key=delivery_key or "",
            worker_redelivery_count=job.worker_redelivery_count,
            application_retry_count=job.application_retry_count,
        )

    if source == "application_retry":
        if job.status not in {
            AutomationJob.Status.RUNNING,
            AutomationJob.Status.RETRYING,
        }:
            raise ExecutionGenerationError(
                "An application retry cannot start from the current job state."
            )
        job.application_retry_count += 1
    elif source == "worker_redelivery":
        if not runner_identity_confirmed:
            raise AccountLockOwnershipError(
                "Worker-loss recovery requires confirmed process identity."
            )
        if job.worker_redelivery_count >= MAX_WORKER_LOSS_REDELIVERIES:
            job.recovery_state = "worker_loss_limit"
            job.save(update_fields=["recovery_state", "updated_at"])
            return ExecutionRecoveryDecision(
                action="worker_loss_limit",
                execution_generation=job.execution_generation,
                delivery_key=delivery_key or "",
                worker_redelivery_count=job.worker_redelivery_count,
                application_retry_count=job.application_retry_count,
            )
        job.worker_redelivery_count += 1
    elif source == "initial":
        if job.status != AutomationJob.Status.QUEUED:
            raise ExecutionGenerationError(
                "Initial execution must start from the queued state."
            )
    else:
        raise ExecutionGenerationError("Unknown execution recovery source.")

    job.execution_generation += 1
    new_generation = job.execution_generation
    if delivery_key is None:
        delivery_key = f"{source}:{job.id}:{new_generation}"
    if len(delivery_key) > 128:
        raise ExecutionGenerationError("delivery_key exceeds 128 characters.")

    job.recovery_delivery_key = delivery_key
    job.recovery_generation = new_generation
    job.recovery_state = "executing"
    job.status = AutomationJob.Status.RUNNING
    job.started_at = job.started_at or now
    job.attempt_count += 1
    job.save(
        update_fields=[
            "execution_generation",
            "application_retry_count",
            "worker_redelivery_count",
            "recovery_delivery_key",
            "recovery_generation",
            "recovery_state",
            "status",
            "started_at",
            "attempt_count",
            "updated_at",
        ]
    )
    if source == "worker_redelivery":
        ExecutionRecoveryRecord.objects.create(
            job=job,
            failed_generation=(
                job.execution_generation - 1
                if failed_generation is None
                else failed_generation
            ),
            recovery_kind="worker_redelivery",
            recovery_delivery_key=delivery_key,
            allocated_generation=new_generation,
        )
    return ExecutionRecoveryDecision(
        action="start_new_generation",
        execution_generation=new_generation,
        delivery_key=delivery_key,
        worker_redelivery_count=job.worker_redelivery_count,
        application_retry_count=job.application_retry_count,
    )


@transaction.atomic
def prepare_worker_loss_recovery(*, job_id):
    """
    Authoritatively prepare a worker-loss recovery in PostgreSQL.
    Idempotent: if recovery is already prepared for the current/failed generation,
    returns the existing decision without re-allocating a generation or re-incrementing counters.
    """
    job = AutomationJob.objects.select_for_update().get(id=job_id)
    if job.status in {
        AutomationJob.Status.SUCCEEDED,
        AutomationJob.Status.FAILED,
        AutomationJob.Status.CANCELLED,
    }:
        return None
    if job.cancel_requested:
        job.status = AutomationJob.Status.CANCELLED
        job.completed_at = timezone.now()
        job.recovery_state = "cancelled"
        job.save(
            update_fields=[
                "status",
                "completed_at",
                "recovery_state",
                "updated_at",
            ]
        )
        return None

    failed_generation = job.execution_generation
    delivery_key = build_worker_recovery_delivery_key(
        job_id=job.id,
        failed_generation=failed_generation,
    )

    existing_record = (
        ExecutionRecoveryRecord.objects.select_for_update()
        .filter(
            job=job,
            failed_generation=failed_generation,
            recovery_kind="worker_redelivery",
        )
        .first()
    )

    if existing_record is not None:
        if job.status not in {
            AutomationJob.Status.QUEUED,
            AutomationJob.Status.RUNNING,
        }:
            job.status = AutomationJob.Status.QUEUED
        job.recovery_delivery_key = existing_record.recovery_delivery_key
        job.recovery_generation = existing_record.allocated_generation
        job.recovery_state = "prepared_recovery"
        job.save(
            update_fields=[
                "status",
                "recovery_delivery_key",
                "recovery_generation",
                "recovery_state",
                "updated_at",
            ]
        )
        return ExecutionRecoveryDecision(
            action="resume_prepared_generation",
            execution_generation=existing_record.allocated_generation,
            delivery_key=existing_record.recovery_delivery_key,
            worker_redelivery_count=job.worker_redelivery_count,
            application_retry_count=job.application_retry_count,
        )

    if job.worker_redelivery_count >= MAX_WORKER_LOSS_REDELIVERIES:
        job.status = AutomationJob.Status.FAILED
        job.error = "Worker loss limit exceeded."
        job.completed_at = timezone.now()
        job.recovery_state = "worker_loss_limit"
        job.save(
            update_fields=[
                "status",
                "error",
                "completed_at",
                "recovery_state",
                "updated_at",
            ]
        )
        return ExecutionRecoveryDecision(
            action="worker_loss_limit",
            execution_generation=job.execution_generation,
            delivery_key=delivery_key,
            worker_redelivery_count=job.worker_redelivery_count,
            application_retry_count=job.application_retry_count,
        )

    new_generation = failed_generation + 1
    job.worker_redelivery_count += 1
    job.execution_generation = new_generation
    job.recovery_delivery_key = delivery_key
    job.recovery_generation = new_generation
    job.recovery_state = "prepared_recovery"
    job.status = AutomationJob.Status.QUEUED
    job.runner_id = None
    job.runner_pid = None
    job.runner_start_ticks = None
    job.runner_container_boot_id = ""
    job.runner_pgid = None
    job.runner_profile_path = ""
    job.runner_ipc_path = ""
    job.runner_state = ""
    job.runner_heartbeat_at = None
    job.save(
        update_fields=[
            "worker_redelivery_count",
            "execution_generation",
            "recovery_delivery_key",
            "recovery_generation",
            "recovery_state",
            "status",
            "runner_id",
            "runner_pid",
            "runner_start_ticks",
            "runner_container_boot_id",
            "runner_pgid",
            "runner_profile_path",
            "runner_ipc_path",
            "runner_state",
            "runner_heartbeat_at",
            "updated_at",
        ]
    )
    ExecutionRecoveryRecord.objects.create(
        job=job,
        failed_generation=failed_generation,
        recovery_kind="worker_redelivery",
        recovery_delivery_key=delivery_key,
        allocated_generation=new_generation,
    )
    return ExecutionRecoveryDecision(
        action="start_new_generation",
        execution_generation=new_generation,
        delivery_key=delivery_key,
        worker_redelivery_count=job.worker_redelivery_count,
        application_retry_count=job.application_retry_count,
    )


@transaction.atomic
def register_browser_runner(
    *,
    account_id,
    job_id,
    owner_token,
    execution_generation,
    runner,
    runner_ipc_path="",
):
    execution_generation = normalize_execution_generation(execution_generation)
    lock = (
        AccountBrowserLock.objects.select_for_update()
        .select_related("job")
        .filter(account_id=account_id, job_id=job_id)
        .first()
    )
    if (
        lock is None
        or not hmac.compare_digest(lock.owner_token_hash, hash_owner_token(owner_token))
        or lock.execution_generation != execution_generation
        or lock.job.execution_generation != execution_generation
    ):
        raise AccountLockOwnershipError("Runner ownership is ambiguous or stale.")

    runner_id = getattr(runner, "runner_id", None)
    runner_pid = getattr(runner, "pid", None)
    runner_start_ticks = getattr(runner, "start_ticks", None)
    runner_container_boot_id = getattr(runner, "container_boot_id", "")
    runner_pgid = getattr(runner, "pgid", None)
    runner_profile_path = getattr(runner, "profile_path", "")
    if (
        runner_id is None
        or type(runner_pid) is not int
        or type(runner_start_ticks) is not int
        or type(runner_pgid) is not int
        or not runner_container_boot_id
        or not runner_profile_path
    ):
        raise AccountLockOwnershipError("Runner identity is incomplete.")

    lock.runner_id = runner_id
    lock.runner_pid = runner_pid
    lock.runner_start_ticks = runner_start_ticks
    lock.runner_container_boot_id = runner_container_boot_id
    lock.runner_pgid = runner_pgid
    lock.runner_profile_path = runner_profile_path
    lock.save(update_fields=[
        "runner_id",
        "runner_pid",
        "runner_start_ticks",
        "runner_container_boot_id",
        "runner_pgid",
        "runner_profile_path",
        "renewed_at",
    ])
    lock.job.runner_id = runner_id
    lock.job.runner_pid = runner_pid
    lock.job.runner_start_ticks = runner_start_ticks
    lock.job.runner_container_boot_id = runner_container_boot_id
    lock.job.runner_pgid = runner_pgid
    lock.job.runner_profile_path = runner_profile_path
    lock.job.runner_ipc_path = runner_ipc_path
    lock.job.runner_state = "running"
    lock.job.runner_heartbeat_at = timezone.now()
    lock.job.save(update_fields=[
        "runner_id",
        "runner_pid",
        "runner_start_ticks",
        "runner_container_boot_id",
        "runner_pgid",
        "runner_profile_path",
        "runner_ipc_path",
        "runner_state",
        "runner_heartbeat_at",
        "updated_at",
    ])
    log_structured(
        logger,
        logging.INFO,
        "runner_registered",
        f"Registered browser runner {runner_id} (PID {runner_pid})",
        job_id=job_id,
        account_id=account_id,
        execution_generation=execution_generation,
        runner_id=runner_id,
        runner_pid=runner_pid,
    )
    return True


@transaction.atomic
def validate_browser_runner(
    *,
    account_id,
    job_id,
    owner_token,
    execution_generation,
):
    execution_generation = normalize_execution_generation(execution_generation)
    lock = (
        AccountBrowserLock.objects.select_for_update()
        .select_related("job")
        .filter(account_id=account_id, job_id=job_id)
        .first()
    )
    job = lock.job if lock is not None else None
    if (
        lock is None
        or job is None
        or not hmac.compare_digest(lock.owner_token_hash, hash_owner_token(owner_token))
        or lock.execution_generation != execution_generation
        or job.execution_generation != execution_generation
        or lock.runner_id is None
        or lock.runner_id != job.runner_id
        or lock.runner_pid != job.runner_pid
        or lock.runner_start_ticks != job.runner_start_ticks
        or lock.runner_pgid != job.runner_pgid
        or lock.runner_container_boot_id != job.runner_container_boot_id
        or not lock.runner_profile_path
    ):
        raise AccountLockOwnershipError("A confirmed browser runner is not available.")

    from orchestrator.runner_ipc import RunnerIdentity, validate_live_process

    identity = RunnerIdentity(
        runner_id=str(lock.runner_id),
        pid=lock.runner_pid,
        start_ticks=lock.runner_start_ticks,
        container_boot_id=lock.runner_container_boot_id,
        pgid=lock.runner_pgid,
        execution_generation=execution_generation,
        job_id=str(lock.job_id),
        profile_path=lock.runner_profile_path,
    )
    if not validate_live_process(identity):
        raise AccountLockOwnershipError("Browser runner process identity is stale or ambiguous.")
    return identity


def reconcile_expired_locks(*, account_id=None):
    locks = AccountBrowserLock.objects.select_related("job").all()
    if account_id is not None:
        locks = locks.filter(account_id=account_id)
    # A database lease expiry is not proof that Chromium or its runner stopped.
    # Only terminal jobs and stale generations may be reconciled here. Live
    # process ownership must be verified by D1.3 process fencing before reuse.
    stale_ids = [
        lock_id
        for lock in locks
        if (
            lock.job.status in {
                AutomationJob.Status.SUCCEEDED,
                AutomationJob.Status.FAILED,
                AutomationJob.Status.CANCELLED,
            }
            or lock.execution_generation != lock.job.execution_generation
        )
        for lock_id in [lock.id]
    ]
    AccountBrowserLock.objects.filter(id__in=stale_ids).delete()
    return len(stale_ids)


@transaction.atomic
def acquire_account_lock(
    *,
    account_id,
    job_id,
    owner_token=None,
    execution_generation,
    ttl_seconds=LOCK_TTL_SECONDS,
):
    execution_generation = normalize_execution_generation(execution_generation)
    account = BotAccount.objects.select_for_update().get(id=account_id)
    now = timezone.now()
    expires_at = now + timedelta(seconds=ttl_seconds)

    job = AutomationJob.objects.select_for_update().get(id=job_id)
    if job.account_id != account.id:
        raise AccountLockOwnershipError("The job does not belong to this account.")
    if execution_generation != job.execution_generation:
        raise ExecutionGenerationError("The requested execution generation is stale.")
    if job.status not in {
        AutomationJob.Status.RUNNING,
        AutomationJob.Status.RETRYING,
        AutomationJob.Status.AWAITING_OTP,
        AutomationJob.Status.CANCELLING,
    }:
        raise AccountLockOwnershipError("A stale or completed job cannot acquire an account lock.")

    lock = AccountBrowserLock.objects.select_for_update().filter(account_id=account.id).first()
    if lock is not None:
        if lock.execution_generation != job.execution_generation:
            lock.delete()
            lock = None
    if lock is not None:
        lock_is_active = (
            lock.expires_at > now
            and lock.job.status
            in {
                AutomationJob.Status.RUNNING,
                AutomationJob.Status.RETRYING,
                AutomationJob.Status.AWAITING_OTP,
                AutomationJob.Status.CANCELLING,
            }
        )
        if lock_is_active:
            if (
                owner_token
                and lock.job_id == job.id
                and lock.execution_generation == job.execution_generation
                and lock.execution_generation == execution_generation
                and hmac.compare_digest(lock.owner_token_hash, hash_owner_token(owner_token))
            ):
                lock.expires_at = expires_at
                lock.save(update_fields=["renewed_at", "expires_at"])
                log_structured(
                    logger,
                    logging.INFO,
                    "lock_acquired",
                    f"Account lock renewed/acquired for account {account_id}",
                    job_id=job_id,
                    account_id=account_id,
                    execution_generation=lock.execution_generation,
                )
                return AccountLock(
                    owner_token=owner_token,
                    expires_at=expires_at,
                    execution_generation=lock.execution_generation,
                )
            log_structured(
                logger,
                logging.WARNING,
                "lock_busy",
                f"Account lock busy for account {account_id}",
                job_id=job_id,
                account_id=account_id,
                execution_generation=execution_generation,
            )
            raise AccountLockBusy("Another job owns this account browser profile.")
        if lock.execution_generation == job.execution_generation:
            log_structured(
                logger,
                logging.WARNING,
                "lock_busy",
                f"Account lock expired without runner termination for account {account_id}",
                job_id=job_id,
                account_id=account_id,
                execution_generation=execution_generation,
            )
            raise AccountLockBusy(
                "The account lock lease expired without confirmed runner termination."
            )
        lock.delete()

    owner_token = owner_token or secrets.token_urlsafe(32)
    lock = AccountBrowserLock.objects.create(
        account=account,
        job=job,
        owner_token_hash=hash_owner_token(owner_token),
        execution_generation=job.execution_generation,
        expires_at=expires_at,
    )
    log_structured(
        logger,
        logging.INFO,
        "lock_acquired",
        f"Account lock acquired for account {account_id}",
        job_id=job_id,
        account_id=account_id,
        execution_generation=lock.execution_generation,
    )
    return AccountLock(
        owner_token=owner_token,
        expires_at=lock.expires_at,
        execution_generation=lock.execution_generation,
    )


@transaction.atomic
def renew_account_lock(
    *,
    account_id,
    job_id,
    owner_token,
    execution_generation,
    ttl_seconds=LOCK_TTL_SECONDS,
):
    execution_generation = normalize_execution_generation(execution_generation)
    lock = (
        AccountBrowserLock.objects.select_for_update()
        .select_related("job")
        .filter(account_id=account_id, job_id=job_id)
        .first()
    )
    if (
        lock is None
        or not hmac.compare_digest(lock.owner_token_hash, hash_owner_token(owner_token))
        or lock.execution_generation != lock.job.execution_generation
        or lock.execution_generation != execution_generation
        or lock.job.execution_generation != execution_generation
        or lock.expires_at <= timezone.now()
        or lock.job.status not in {
            AutomationJob.Status.RUNNING,
            AutomationJob.Status.RETRYING,
            AutomationJob.Status.AWAITING_OTP,
            AutomationJob.Status.CANCELLING,
        }
    ):
        raise AccountLockOwnershipError("The account lock is not owned by this job.")
    expires_at = timezone.now() + timedelta(seconds=ttl_seconds)
    lock.expires_at = expires_at
    lock.save(update_fields=["renewed_at", "expires_at"])
    return expires_at


@transaction.atomic
def validate_account_lock(*, account_id, job_id, owner_token, execution_generation):
    execution_generation = normalize_execution_generation(execution_generation)
    lock = (
        AccountBrowserLock.objects.select_for_update()
        .filter(account_id=account_id, job_id=job_id)
        .first()
    )
    if (
        lock is None
        or not hmac.compare_digest(lock.owner_token_hash, hash_owner_token(owner_token))
        or lock.execution_generation != lock.job.execution_generation
        or lock.execution_generation != execution_generation
        or lock.job.execution_generation != execution_generation
        or lock.expires_at <= timezone.now()
        or lock.job.status not in {
            AutomationJob.Status.RUNNING,
            AutomationJob.Status.RETRYING,
            AutomationJob.Status.AWAITING_OTP,
            AutomationJob.Status.CANCELLING,
        }
    ):
        raise AccountLockOwnershipError("A valid owner lock is required for this account operation.")
    return True


@transaction.atomic
def release_account_lock(*, account_id, job_id, owner_token, execution_generation):
    execution_generation = normalize_execution_generation(execution_generation)
    lock = (
        AccountBrowserLock.objects.select_for_update()
        .filter(account_id=account_id, job_id=job_id)
        .first()
    )
    if lock is None:
        return False
    if not hmac.compare_digest(lock.owner_token_hash, hash_owner_token(owner_token)):
        raise AccountLockOwnershipError("Only the lock owner can release this account lock.")
    if lock.execution_generation != lock.job.execution_generation:
        raise AccountLockOwnershipError("A stale execution cannot release the account lock.")
    if (
        lock.execution_generation != execution_generation
        or lock.job.execution_generation != execution_generation
    ):
        raise AccountLockOwnershipError("A stale execution cannot release the account lock.")
    if lock.runner_id is not None:
        from orchestrator.runner_ipc import RunnerIdentity, validate_live_process
        if (
            lock.runner_pid is None
            or lock.runner_start_ticks is None
            or lock.runner_pgid is None
            or not lock.runner_container_boot_id
            or not lock.runner_profile_path
        ):
            raise AccountLockOwnershipError("The browser runner identity is incomplete.")
        identity = RunnerIdentity(
            runner_id=str(lock.runner_id),
            pid=lock.runner_pid,
            start_ticks=lock.runner_start_ticks,
            container_boot_id=lock.runner_container_boot_id,
            pgid=lock.runner_pgid,
            execution_generation=execution_generation,
            job_id=str(lock.job_id),
            profile_path=lock.runner_profile_path,
        )
        if validate_live_process(identity):
            raise AccountLockOwnershipError(
                "The browser runner must be positively terminated before lock release."
            )
    log_structured(
        logger,
        logging.INFO,
        "lock_released",
        f"Account lock released for account {account_id}",
        job_id=job_id,
        account_id=account_id,
        execution_generation=execution_generation,
        runner_id=str(lock.runner_id) if lock.runner_id else None,
    )
    lock.delete()
    return True
