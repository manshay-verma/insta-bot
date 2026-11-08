import asyncio
import logging
import sys
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone
from asgiref.sync import sync_to_async
from redis import asyncio as redis_async

from .models import AutomationJob
from .logging import log_structured
from .account_locks import (
    AccountLockBusy,
    AccountLockOwnershipError,
    ExecutionGenerationError,
    acquire_account_lock,
    normalize_execution_generation,
    release_account_lock,
    renew_account_lock,
    register_browser_runner,
    validate_browser_runner,
    resolve_execution_recovery,
    build_worker_recovery_delivery_key,
)
from .verification import OTP_TIMEOUT_SECONDS, otp_redis_key

logger = logging.getLogger(__name__)


def _result_summary(result, targets):
    return {
        "success": bool(result.success),
        "items_processed": result.items_processed,
        "errors": list(result.errors or []),
        "processed": targets[: result.items_processed],
    }


def _set_job_failure(job_id, message, execution_generation, result=None):
    failed_at = timezone.now()
    execution_generation = normalize_execution_generation(execution_generation)
    filters = {
        "status__in": (
            AutomationJob.Status.QUEUED,
            AutomationJob.Status.RUNNING,
            AutomationJob.Status.RETRYING,
            AutomationJob.Status.AWAITING_OTP,
            AutomationJob.Status.CANCELLING,
        ),
        "execution_generation": execution_generation,
    }
    AutomationJob.objects.filter(
        id=job_id,
        **filters,
    ).update(
        status=AutomationJob.Status.FAILED,
        error=message,
        result=result,
        completed_at=failed_at,
        verification_expires_at=None,
        updated_at=failed_at,
    )


async def _wait_for_job_otp(job_id, execution_generation):
    expires_at = timezone.now() + timedelta(seconds=OTP_TIMEOUT_SECONDS)
    marked_pending = await sync_to_async(
        lambda: AutomationJob.objects.filter(
            id=job_id,
            status=AutomationJob.Status.RUNNING,
            cancel_requested=False,
            execution_generation=execution_generation,
        ).update(
            status=AutomationJob.Status.AWAITING_OTP,
            verification_expires_at=expires_at,
            updated_at=timezone.now(),
        ),
        thread_sensitive=True,
    )()
    if not marked_pending:
        raise RuntimeError("The automation job is no longer accepting verification codes.")

    redis_client = redis_async.from_url(
        settings.CELERY_BROKER_URL,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    key = otp_redis_key(job_id, execution_generation)
    try:
        while timezone.now() < expires_at:
            code = await redis_client.getdel(key)
            if code is not None:
                resumed = await sync_to_async(
                    lambda: AutomationJob.objects.filter(
                        id=job_id,
                        status=AutomationJob.Status.AWAITING_OTP,
                        cancel_requested=False,
                        execution_generation=execution_generation,
                    ).update(
                        status=AutomationJob.Status.RUNNING,
                        verification_expires_at=None,
                        updated_at=timezone.now(),
                    ),
                    thread_sensitive=True,
                )()
                if not resumed:
                    raise RuntimeError(
                        "The automation job was cancelled before verification resumed."
                    )
                await redis_client.delete(key)
                return code

            job_state = await sync_to_async(
                lambda: AutomationJob.objects.filter(
                    id=job_id,
                    execution_generation=execution_generation,
                ).values("status", "cancel_requested").first(),
                thread_sensitive=True,
            )()
            if (
                job_state is None
                or job_state["cancel_requested"]
                or job_state["status"] != AutomationJob.Status.AWAITING_OTP
            ):
                raise RuntimeError(
                    "The automation job stopped waiting for verification."
                )
            await asyncio.sleep(0.5)

        failed_at = timezone.now()
        await sync_to_async(
            lambda: AutomationJob.objects.filter(
                id=job_id,
                status=AutomationJob.Status.AWAITING_OTP,
                execution_generation=execution_generation,
            ).update(
                status=AutomationJob.Status.FAILED,
                error="The verification code was not submitted before the challenge expired.",
                completed_at=failed_at,
                verification_expires_at=None,
                updated_at=failed_at,
            ),
            thread_sensitive=True,
        )()
        raise TimeoutError("The verification code submission timed out.")
    finally:
        try:
            await redis_client.delete(key)
        finally:
            await redis_client.aclose()


@shared_task(bind=True, name="api.execute_automation_job")
def execute_automation_job(
    self,
    job_id,
    lock_owner_token=None,
    execution_generation=None,
    delivery_reason="initial",
    recovery_delivery_key=None,
    recovery_resume=False,
    runner_identity_confirmed=False,
):
    """Execute one durable job in the Celery automation-worker process."""
    close_old_connections()
    job = None
    lock_owner_token = lock_owner_token
    if execution_generation is not None:
        try:
            execution_generation = normalize_execution_generation(execution_generation)
        except ExecutionGenerationError:
            return {
                "job_id": str(job_id),
                "status": "invalid_execution_generation",
            }
    try:
        with transaction.atomic():
            job = AutomationJob.objects.select_for_update().get(id=job_id)
            if self.request.id:
                job.celery_task_id = self.request.id
            job.save(update_fields=["celery_task_id", "updated_at"])
            source = (
                "application_retry"
                if delivery_reason == "application_retry"
                else "worker_redelivery"
                if delivery_reason == "worker_redelivery"
                else "initial"
            )
            if recovery_delivery_key is None:
                if source == "initial":
                    recovery_delivery_key = (
                        f"initial:{job.id}:{self.request.id or 'delivery'}"
                    )
                elif source == "application_retry":
                    recovery_delivery_key = (
                        f"application:{job.id}:{job.execution_generation + 1}"
                    )
                elif source == "worker_redelivery":
                    failed_generation = (
                        execution_generation
                        if execution_generation is not None
                        else job.execution_generation
                    )
                    recovery_delivery_key = build_worker_recovery_delivery_key(
                        job_id=job.id,
                        failed_generation=failed_generation,
                    )
            try:
                decision = resolve_execution_recovery(
                    job_id=job.id,
                    source=source,
                    delivery_key=recovery_delivery_key,
                    supplied_generation=execution_generation,
                    owner_token=lock_owner_token,
                    recovery_resume=recovery_resume,
                    runner_identity_confirmed=runner_identity_confirmed,
                )
            except ExecutionGenerationError as exc:
                log_structured(
                    logger, logging.WARNING, "recovery_rejected",
                    "Execution recovery rejected (generation mismatch)",
                    job_id=str(job.id), account_id=job.account_id,
                    execution_generation=execution_generation,
                    error_type=type(exc).__name__,
                )
                return {"job_id": str(job.id), "status": job.status, "recovery_rejected": True}
            except AccountLockOwnershipError as exc:
                log_structured(
                    logger, logging.WARNING, "recovery_rejected",
                    "Execution recovery ownership rejected",
                    job_id=str(job.id), account_id=job.account_id,
                    execution_generation=execution_generation,
                    error_type=type(exc).__name__,
                )
                return {"job_id": str(job.id), "status": job.status, "recovery_rejected": True}

            if decision.action in {"duplicate_delivery", "otp_reconnect"}:
                if decision.action == "otp_reconnect":
                    try:
                        identity = validate_browser_runner(
                            account_id=job.account_id,
                            job_id=job.id,
                            owner_token=lock_owner_token,
                            execution_generation=decision.execution_generation,
                        )
                        if not job.runner_ipc_path:
                            raise AccountLockOwnershipError(
                                "Confirmed runner IPC endpoint is unavailable."
                            )
                        from orchestrator.runner_supervisor import (
                            BrowserRunnerSupervisor,
                            RunnerSupervisorError,
                        )

                        reconnect_supervisor = BrowserRunnerSupervisor(
                            job_id=job.id,
                            account_id=job.account_id,
                            execution_generation=decision.execution_generation,
                            lock_owner_token=lock_owner_token,
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
                            existing_socket_path=job.runner_ipc_path,
                        )
                        async def reconnect_existing_runner():
                            await reconnect_supervisor.reconnect(timeout_seconds=10)
                            await reconnect_supervisor.request("identity")

                        asyncio.run(reconnect_existing_runner())
                    except (AccountLockOwnershipError, RunnerSupervisorError):
                        return {
                            "job_id": str(job.id),
                            "status": job.status,
                            "recovery_rejected": True,
                        }
                return {
                    "job_id": str(job.id),
                    "status": job.status,
                    "execution_generation": decision.execution_generation,
                    "duplicate_delivery": decision.action == "duplicate_delivery",
                    "awaiting_otp": decision.action == "otp_reconnect",
                }
            if decision.action == "worker_loss_limit":
                return {
                    "job_id": str(job.id),
                    "status": job.status,
                    "execution_generation": decision.execution_generation,
                    "worker_loss_limit": True,
                }
            execution_generation = decision.execution_generation

        try:
            account_lock = acquire_account_lock(
                account_id=job.account_id,
                job_id=job.id,
                owner_token=lock_owner_token,
                execution_generation=job.execution_generation,
            )
            lock_owner_token = account_lock.owner_token
            execution_generation = getattr(
                account_lock,
                "execution_generation",
                execution_generation,
            )
        except (AccountLockBusy, AccountLockOwnershipError) as exc:
            _set_job_failure(
                job.id,
                str(exc),
                execution_generation=job.execution_generation,
            )
            log_structured(
                logger, logging.WARNING, "lock_acquire_failed",
                "Automation job could not acquire its account lock",
                job_id=str(job.id), account_id=job.account_id,
                execution_generation=job.execution_generation,
                error_type=type(exc).__name__,
                task_id=self.request.id,
            )
            return {"job_id": str(job.id), "status": AutomationJob.Status.FAILED}

        from orchestrator import AdapterType, TaskType

        action_map = {
            "like": TaskType.LIKE_POSTS,
            "follow": TaskType.FOLLOW_USERS,
            "unfollow": TaskType.UNFOLLOW_USERS,
            "scrape_profile": TaskType.SCRAPE_PROFILE,
            "view_stories": TaskType.VIEW_STORIES,
            "download": TaskType.BULK_DOWNLOAD,
            "comment": TaskType.COMMENT,
        }
        task_type = action_map.get(job.action)
        if task_type is None:
            raise ValueError(f"Unsupported automation action: {job.action}")

        adapter_type = (
            AdapterType.DOWNLOADER
            if job.action == "download"
            else AdapterType.PLAYWRIGHT
        )
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        log_structured(
            logger, logging.INFO, "job_started",
            "Automation job starting execution",
            job_id=str(job.id), account_id=job.account_id,
            execution_generation=execution_generation,
            action=job.action,
            attempt_count=job.attempt_count,
            task_id=self.request.id,
        )

        async def run_job():
            from orchestrator.runner_supervisor import BrowserRunnerSupervisor
            from types import SimpleNamespace

            supervisor = BrowserRunnerSupervisor(
                job_id=job.id,
                account_id=job.account_id,
                execution_generation=execution_generation,
                lock_owner_token=lock_owner_token,
                adapter_type=getattr(adapter_type, "value", adapter_type),
                task_type=getattr(task_type, "value", task_type),
                targets=job.targets,
                options=dict(job.options),
            )
            identity = supervisor.start()
            await sync_to_async(register_browser_runner, thread_sensitive=True)(
                account_id=job.account_id,
                job_id=job.id,
                owner_token=lock_owner_token,
                execution_generation=execution_generation,
                runner=identity,
                runner_ipc_path=str(supervisor.socket_path),
            )
            await supervisor.reconnect(timeout_seconds=10)

            async def renew_lock_heartbeat():
                while True:
                    await asyncio.sleep(300)
                    try:
                        await sync_to_async(
                            renew_account_lock,
                            thread_sensitive=True,
                        )(
                            account_id=job.account_id,
                            job_id=job.id,
                            owner_token=lock_owner_token,
                            execution_generation=execution_generation,
                        )
                    except Exception:
                        await supervisor.disable_actions()
                        raise

            heartbeat_task = asyncio.create_task(renew_lock_heartbeat())
            try:
                response = await supervisor.execute()
                result = response["result"]
                return SimpleNamespace(
                    success=bool(result["success"]),
                    items_processed=int(result["items_processed"]),
                    errors=list(result["errors"]),
                    data=result.get("data"),
                )
            finally:
                try:
                    await supervisor.close()
                finally:
                    heartbeat_task.cancel()
                    await asyncio.gather(heartbeat_task, return_exceptions=True)

        result = asyncio.run(run_job())
        summary = _result_summary(result, job.targets)
        finished_at = timezone.now()
        with transaction.atomic():
            current = AutomationJob.objects.select_for_update().get(id=job.id)
            if getattr(current, "execution_generation", execution_generation) != execution_generation:
                log_structured(
                    logger, logging.WARNING, "stale_generation_rejected",
                    "Stale execution result rejected",
                    job_id=str(job.id),
                    execution_generation=execution_generation,
                    current_generation=current.execution_generation,
                )
                return {"job_id": str(job.id), "status": current.status, "stale_generation": True}
            if current.cancel_requested:
                current.status = AutomationJob.Status.CANCELLED
            else:
                current.status = (
                    AutomationJob.Status.SUCCEEDED
                    if result.success
                    else AutomationJob.Status.FAILED
                )
            current.result = summary
            current.error = "" if result.success else "; ".join(result.errors or [])
            current.completed_at = finished_at
            current.verification_expires_at = None
            current.save(
                update_fields=[
                    "status",
                    "result",
                    "error",
                    "completed_at",
                    "verification_expires_at",
                    "updated_at",
                ]
            )
        log_structured(
            logger, logging.INFO, "job_finished",
            "Automation job finished",
            job_id=str(job.id), account_id=job.account_id,
            execution_generation=execution_generation,
            status=current.status,
            action=job.action,
            attempt_count=job.attempt_count,
            task_id=self.request.id,
        )
        return {"job_id": str(job.id), "status": current.status, **summary}
    except Exception as exc:
        if job is not None:
            job.refresh_from_db()
        if (
            job is not None
            and job.status == AutomationJob.Status.RUNNING
            and job.action == "scrape_profile"
            and self.request.retries < 2
        ):
            try:
                release_account_lock(
                    account_id=job.account_id,
                    job_id=job.id,
                    owner_token=lock_owner_token,
                    execution_generation=execution_generation,
                )
            except Exception:
                logger.warning(
                    "Could not release account lock before retry scheduling",
                    extra={"job_id": str(job.id), "account_id": job.account_id},
                )
            job.status = AutomationJob.Status.RETRYING
            job.error = f"Transient worker failure ({type(exc).__name__}); retry scheduled."
            job.save(update_fields=["status", "error", "updated_at"])
            log_structured(
                logger, logging.WARNING, "job_retry_scheduled",
                "Automation job scheduled for retry",
                job_id=str(job.id), account_id=job.account_id,
                execution_generation=execution_generation,
                retry_count=self.request.retries,
                error_type=type(exc).__name__,
            )
            raise self.retry(
                exc=exc,
                countdown=min(30, 2 ** (self.request.retries + 1)),
                max_retries=2,
                kwargs={
                    "lock_owner_token": lock_owner_token,
                    "execution_generation": execution_generation,
                    "delivery_reason": "application_retry",
                    "recovery_delivery_key": (
                        f"application:{job.id}:{execution_generation + 1}"
                    ),
                },
            )
        if job is not None:
            _set_job_failure(
                job.id,
                f"Worker execution failed ({type(exc).__name__}).",
                execution_generation=execution_generation,
            )
        log_structured(
            logger, logging.ERROR, "job_execution_failed",
            "Automation job execution raised an exception",
            job_id=str(job.id) if job else str(job_id),
            account_id=job.account_id if job else None,
            execution_generation=execution_generation,
            error_type=type(exc).__name__,
            action=job.action if job else None,
            task_id=self.request.id,
        )
        raise
    finally:
        if job is not None and lock_owner_token is not None:
            try:
                release_account_lock(
                    account_id=job.account_id,
                    job_id=job.id,
                    owner_token=lock_owner_token,
                    execution_generation=execution_generation,
                )
            except Exception:
                logger.warning(
                    "Account lock cleanup failed",
                    extra={
                        "job_id": str(job.id),
                        "account_id": job.account_id,
                        "task_id": self.request.id,
                    },
                )
        close_old_connections()


@shared_task(bind=True, name="api.healthcheck")
def worker_healthcheck(self):
    from .account_locks import reconcile_expired_locks

    reconciled = reconcile_expired_locks()
    return {
        "ok": True,
        "worker": self.request.hostname,
        "checked_at": timezone.now().isoformat(),
        "locks_reconciled": reconciled,
    }
