import asyncio
import json
import logging
import os
import signal
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from celery import bootsteps
from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone
import redis

from .models import AccountBrowserLock, AutomationJob, ExecutionRecoveryRecord
from .account_locks import (
    MAX_WORKER_LOSS_REDELIVERIES,
    AccountLockOwnershipError,
    build_worker_recovery_delivery_key,
    prepare_worker_loss_recovery,
    reconcile_expired_locks,
)
from .logging import log_structured
from orchestrator.runner_ipc import RunnerIdentity, validate_live_process
from orchestrator.runner_supervisor import (
    BrowserRunnerSupervisor,
    RunnerSupervisorError,
)

logger = logging.getLogger(__name__)

STARTUP_RECONCILIATION_LOCK_ID = 5282367123169727043


def is_celery_task_present(celery_task_id: str, *, redis_client: Optional[redis.Redis] = None) -> bool:
    """
    Check if a Celery task ID is present in the broker Redis queues.
    Returns False if task ID is empty or not found in Redis, or on broker failure.
    """
    if not celery_task_id:
        return False
    close_client = False
    if redis_client is None:
        try:
            broker_url = getattr(settings, "CELERY_BROKER_URL", "redis://redis:6379/0")
            redis_client = redis.from_url(
                broker_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            close_client = True
        except Exception as exc:
            logger.warning("Could not connect to Redis to inspect Celery queue: %s", exc)
            return False

    try:
        # Check standard Celery queue list (default: 'celery')
        queue_items = redis_client.lrange("celery", 0, -1)
        for raw in queue_items:
            try:
                payload = json.loads(raw)
                # Kombu message format: headers['id'] or id
                task_id = payload.get("headers", {}).get("id") or payload.get("id")
                if task_id == celery_task_id:
                    return True
            except Exception:
                continue

        # Check unacked hash if present
        unacked = redis_client.hkeys("unacked")
        if unacked and celery_task_id in [u if isinstance(u, str) else u.decode("utf-8") for u in unacked]:
            return True

        return False
    except Exception as exc:
        logger.warning("Error checking Celery task presence in Redis: %s", exc)
        return False
    finally:
        if close_client and redis_client is not None:
            try:
                redis_client.close()
            except Exception:
                pass


def reconnect_live_runner(
    job: AutomationJob,
    lock: Optional[AccountBrowserLock] = None,
    *,
    timeout_seconds: float = 5.0,
) -> Tuple[bool, Optional[RunnerIdentity]]:
    """
    Verify whether the recorded browser runner process is live and responsive
    via authenticated IPC. Returns (True, identity) or (False, None).
    """
    runner_id = job.runner_id or (lock.runner_id if lock else None)
    runner_pid = job.runner_pid or (lock.runner_pid if lock else None)
    runner_start_ticks = job.runner_start_ticks or (lock.runner_start_ticks if lock else None)
    runner_container_boot_id = job.runner_container_boot_id or (lock.runner_container_boot_id if lock else "")
    runner_pgid = job.runner_pgid or (lock.runner_pgid if lock else None)
    runner_profile_path = job.runner_profile_path or (lock.runner_profile_path if lock else "")
    runner_ipc_path = job.runner_ipc_path

    if (
        runner_id is None
        or runner_pid is None
        or runner_start_ticks is None
        or runner_pgid is None
        or not runner_container_boot_id
        or not runner_profile_path
    ):
        return False, None

    identity = RunnerIdentity(
        runner_id=str(runner_id),
        pid=runner_pid,
        start_ticks=runner_start_ticks,
        container_boot_id=runner_container_boot_id,
        pgid=runner_pgid,
        execution_generation=job.execution_generation,
        job_id=str(job.id),
        profile_path=runner_profile_path,
    )

    if not validate_live_process(identity):
        return False, None

    if not runner_ipc_path or not Path(runner_ipc_path).exists():
        return False, None

    supervisor = BrowserRunnerSupervisor(
        job_id=job.id,
        account_id=job.account_id,
        execution_generation=job.execution_generation,
        lock_owner_token="",  # Handshake uses INSTABOT_RUNNER_IPC_SECRET
        adapter_type="playwright",
        task_type=job.action,
        targets=job.targets,
        existing_identity={
            "runner_id": str(identity.runner_id),
            "pid": identity.pid,
            "start_ticks": identity.start_ticks,
            "container_boot_id": identity.container_boot_id,
            "pgid": identity.pgid,
        },
        existing_socket_path=runner_ipc_path,
    )

    async def probe_runner():
        await supervisor.reconnect(timeout_seconds=timeout_seconds)
        resp = await supervisor.request("identity")
        return resp.get("ok") is True

    try:
        ok = asyncio.run(probe_runner())
        if ok:
            return True, identity
    except Exception as exc:
        logger.warning(
            "Live runner probe failed",
            extra={"job_id": str(job.id), "error": str(exc)},
        )

    return False, None


def terminate_orphaned_process_group(pgid: Optional[int], grace_seconds: float = 3.0) -> None:
    """Safely terminate an orphaned runner process group with SIGTERM then SIGKILL."""
    if not pgid or pgid <= 0:
        return
    try:
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return

    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        try:
            os.killpg(pgid, 0)
            time.sleep(0.05)
        except (ProcessLookupError, PermissionError):
            return

    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


@transaction.atomic
def reconcile_single_job(
    job_id: Any,
    *,
    redis_client: Optional[redis.Redis] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Authoritatively reconcile one automation job.
    Uses PostgreSQL transaction and row-level select_for_update.
    """
    job = AutomationJob.objects.select_for_update().get(id=job_id)
    lock = (
        AccountBrowserLock.objects.select_for_update()
        .filter(account_id=job.account_id, job_id=job.id)
        .first()
    )
    now = timezone.now()

    # Case 1: Terminal job
    if job.status in {
        AutomationJob.Status.SUCCEEDED,
        AutomationJob.Status.FAILED,
        AutomationJob.Status.CANCELLED,
    }:
        if lock is not None:
            lock.delete()
        log_structured(logger, logging.DEBUG, "reconcile_noop_terminal",
            "Reconciliation: terminal job skipped",
            job_id=str(job.id), account_id=job.account_id,
            execution_generation=job.execution_generation, status=job.status)
        return {"action": "noop_terminal", "job_id": str(job.id), "status": job.status}

    # Case 2: Cancellation requested or CANCELLING
    if job.cancel_requested or job.status == AutomationJob.Status.CANCELLING:
        runner_pgid = job.runner_pgid or (lock.runner_pgid if lock else None)
        terminate_orphaned_process_group(runner_pgid)
        if lock is not None:
            lock.delete()
        if job.runner_ipc_path and os.path.exists(job.runner_ipc_path):
            try:
                os.unlink(job.runner_ipc_path)
            except OSError:
                pass

        job.status = AutomationJob.Status.CANCELLED
        job.completed_at = now
        job.verification_expires_at = None
        job.recovery_state = "cancelled"
        job.runner_state = "terminated"
        job.error = job.error or "Cancelled during startup reconciliation."
        job.save(
            update_fields=[
                "status",
                "completed_at",
                "verification_expires_at",
                "recovery_state",
                "runner_state",
                "error",
                "updated_at",
            ]
        )
        return {"action": "cancelled", "job_id": str(job.id), "status": job.status}

    # Case 3: AWAITING_OTP
    if job.status == AutomationJob.Status.AWAITING_OTP:
        if job.verification_expires_at is None or job.verification_expires_at <= now:
            # Challenge expired
            runner_pgid = job.runner_pgid or (lock.runner_pgid if lock else None)
            terminate_orphaned_process_group(runner_pgid)
            if lock is not None:
                lock.delete()
            if job.runner_ipc_path and os.path.exists(job.runner_ipc_path):
                try:
                    os.unlink(job.runner_ipc_path)
                except OSError:
                    pass

            job.status = AutomationJob.Status.FAILED
            job.error = "The verification challenge expired."
            job.completed_at = now
            job.verification_expires_at = None
            job.recovery_state = "otp_expired"
            job.runner_state = "terminated"
            job.save(
                update_fields=[
                    "status",
                    "error",
                    "completed_at",
                    "verification_expires_at",
                    "recovery_state",
                    "runner_state",
                    "updated_at",
                ]
            )
            return {"action": "otp_expired", "job_id": str(job.id), "status": job.status}

        # Unexpired OTP challenge
        # NEVER launch a replacement browser for an unexpired OTP challenge!
        is_live, identity = reconnect_live_runner(job, lock)
        if is_live:
            job.runner_heartbeat_at = now
            job.runner_state = "awaiting_otp"
            job.save(update_fields=["runner_heartbeat_at", "runner_state", "updated_at"])
            return {"action": "otp_reconnected", "job_id": str(job.id), "status": job.status}
        else:
            # Fail closed for dead or ambiguous runner
            runner_pgid = job.runner_pgid or (lock.runner_pgid if lock else None)
            terminate_orphaned_process_group(runner_pgid)
            if lock is not None:
                lock.delete()
            if job.runner_ipc_path and os.path.exists(job.runner_ipc_path):
                try:
                    os.unlink(job.runner_ipc_path)
                except OSError:
                    pass

            job.status = AutomationJob.Status.FAILED
            job.error = "Browser runner process terminated during verification challenge."
            job.completed_at = now
            job.verification_expires_at = None
            job.recovery_state = "runner_lost"
            job.runner_state = "dead"
            job.save(
                update_fields=[
                    "status",
                    "error",
                    "completed_at",
                    "verification_expires_at",
                    "recovery_state",
                    "runner_state",
                    "updated_at",
                ]
            )
            return {
                "action": "otp_failed_runner_lost",
                "job_id": str(job.id),
                "status": job.status,
            }

    # Case 4: Stale RUNNING or RETRYING
    if job.status in {AutomationJob.Status.RUNNING, AutomationJob.Status.RETRYING}:
        is_live, identity = reconnect_live_runner(job, lock)
        if is_live:
            job.runner_heartbeat_at = now
            job.runner_state = "running"
            job.save(update_fields=["runner_heartbeat_at", "runner_state", "updated_at"])
            return {"action": "runner_reconnected", "job_id": str(job.id), "status": job.status}

        # Runner is dead or unverified -> Dead runner recovery
        runner_pgid = job.runner_pgid or (lock.runner_pgid if lock else None)
        terminate_orphaned_process_group(runner_pgid)
        if lock is not None:
            lock.delete()
        if job.runner_ipc_path and os.path.exists(job.runner_ipc_path):
            try:
                os.unlink(job.runner_ipc_path)
            except OSError:
                pass

        decision = prepare_worker_loss_recovery(job_id=job.id)
        if decision is None:
            return {"action": "noop", "job_id": str(job.id), "status": job.status}
        if decision.action == "worker_loss_limit":
            job.refresh_from_db()
            return {
                "action": "worker_loss_limit",
                "job_id": str(job.id),
                "status": job.status,
                "execution_generation": job.execution_generation,
            }
        if decision.action in {"start_new_generation", "resume_prepared_generation"}:
            from .tasks import execute_automation_job

            task = execute_automation_job.delay(
                job_id=str(job.id),
                execution_generation=decision.execution_generation,
                delivery_reason="worker_redelivery",
                recovery_delivery_key=decision.delivery_key,
            )
            job.celery_task_id = task.id
            job.save(update_fields=["celery_task_id", "updated_at"])
            return {
                "action": "recovered_worker_loss",
                "job_id": str(job.id),
                "generation": decision.execution_generation,
                "task_id": task.id,
                "status": job.status,
            }

    # Case 5: QUEUED job (Lost Celery message recovery)
    if job.status == AutomationJob.Status.QUEUED:
        # Check if the task is present in broker
        task_present = is_celery_task_present(job.celery_task_id, redis_client=redis_client)
        if not task_present:
            from .tasks import execute_automation_job

            delivery_reason = (
                "worker_redelivery"
                if job.recovery_delivery_key
                else "initial"
            )
            task = execute_automation_job.delay(
                job_id=str(job.id),
                execution_generation=job.execution_generation,
                delivery_reason=delivery_reason,
                recovery_delivery_key=job.recovery_delivery_key,
            )
            job.celery_task_id = task.id
            job.save(update_fields=["celery_task_id", "updated_at"])
            return {
                "action": "redelivered_lost_task",
                "job_id": str(job.id),
                "task_id": task.id,
                "status": job.status,
            }
        else:
            return {
                "action": "queued_task_healthy",
                "job_id": str(job.id),
                "status": job.status,
            }

    return {"action": "unhandled", "job_id": str(job.id), "status": job.status}


def reconcile_startup_jobs(
    *,
    redis_client: Optional[redis.Redis] = None,
    blocking: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Authoritative startup reconciliation of all non-terminal automation jobs.
    Protected by PostgreSQL transaction advisory lock to guarantee concurrent safety.
    Returns metrics including duration, action counters, and per-job results.
    """
    start_time = time.monotonic()
    log_structured(logger, logging.INFO, "reconciliation_started",
        "Startup reconciliation beginning")
    results = []

    # Action counters for metrics
    action_counts: Dict[str, int] = {}

    with transaction.atomic():
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                if blocking:
                    cursor.execute(
                        "SELECT pg_advisory_xact_lock(%s);",
                        [STARTUP_RECONCILIATION_LOCK_ID],
                    )
                else:
                    cursor.execute(
                        "SELECT pg_try_advisory_xact_lock(%s);",
                        [STARTUP_RECONCILIATION_LOCK_ID],
                    )
                    acquired = cursor.fetchone()[0]
                    if not acquired:
                        logger.info("Concurrent startup reconciliation in progress; skipping.")
                        duration_ms = int((time.monotonic() - start_time) * 1000)
                        log_structured(logger, logging.INFO, "reconciliation_skipped",
                            "Concurrent startup reconciliation in progress; skipped",
                            duration_ms=duration_ms)
                        return {
                            "reconciled_jobs": 0,
                            "results": [],
                            "skipped_concurrent": True,
                            "duration_ms": duration_ms,
                        }

        # Query all active or non-terminal jobs authoritatively from PostgreSQL
        active_statuses = [
            AutomationJob.Status.QUEUED,
            AutomationJob.Status.RUNNING,
            AutomationJob.Status.RETRYING,
            AutomationJob.Status.AWAITING_OTP,
            AutomationJob.Status.CANCELLING,
        ]
        job_ids = list(
            AutomationJob.objects.filter(status__in=active_statuses)
            .order_by("created_at")
            .values_list("id", flat=True)
        )

        for job_id in job_ids:
            try:
                res = reconcile_single_job(
                    job_id,
                    redis_client=redis_client,
                    dry_run=dry_run,
                )
                results.append(res)
                action = res.get("action", "unknown")
                action_counts[action] = action_counts.get(action, 0) + 1
                log_structured(logger, logging.INFO, "reconcile_job_action",
                    f"Reconciled job: {action}",
                    job_id=res.get("job_id"), action=action, status=res.get("status"))
            except Exception as exc:
                log_structured(logger, logging.ERROR, "reconcile_job_error",
                    f"Error reconciling job {job_id}: {exc}",
                    job_id=str(job_id), error_type=type(exc).__name__)
                logger.error(
                    "Error reconciling job %s: %s",
                    job_id,
                    exc,
                    exc_info=True,
                )
                results.append({"action": "error", "job_id": str(job_id), "error": str(exc)})
                action_counts["error"] = action_counts.get("error", 0) + 1

        reconciled_locks = reconcile_expired_locks()

    duration_ms = int((time.monotonic() - start_time) * 1000)
    log_structured(
        logger, logging.INFO, "reconciliation_completed",
        "Startup reconciliation completed",
        jobs_scanned=len(job_ids),
        locks_reconciled=reconciled_locks,
        duration_ms=duration_ms,
        **action_counts,
    )
    return {
        "reconciled_jobs": len(job_ids),
        "results": results,
        "locks_reconciled": reconciled_locks,
        "duration_ms": duration_ms,
        "action_counts": action_counts,
    }


class StartupReconciliationStep(bootsteps.StartStopStep):
    """
    Celery consumer bootstep:
    Runs startup reconciliation before the worker consumer starts consuming tasks.
    """

    requires = {"celery.worker.consumer.tasks:Tasks"}

    def start(self, consumer):
        logger.info("StartupReconciliationStep: Reconciling jobs before consuming tasks...")
        try:
            reconcile_startup_jobs(blocking=True)
        except Exception as exc:
            logger.error("StartupReconciliationStep failed during reconciliation: %s", exc, exc_info=True)
            # Worker must fail closed or log critical error
            raise

