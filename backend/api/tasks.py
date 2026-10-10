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
from .verification import OTP_TIMEOUT_SECONDS, otp_redis_key

logger = logging.getLogger(__name__)


def _result_summary(result, targets):
    return {
        "success": bool(result.success),
        "items_processed": result.items_processed,
        "errors": list(result.errors or []),
        "processed": targets[: result.items_processed],
    }


def _set_job_failure(job_id, message, result=None):
    failed_at = timezone.now()
    AutomationJob.objects.filter(
        id=job_id,
        status__in=(
            AutomationJob.Status.QUEUED,
            AutomationJob.Status.RUNNING,
            AutomationJob.Status.RETRYING,
            AutomationJob.Status.AWAITING_OTP,
            AutomationJob.Status.CANCELLING,
        ),
    ).update(
        status=AutomationJob.Status.FAILED,
        error=message,
        result=result,
        completed_at=failed_at,
        verification_expires_at=None,
        updated_at=failed_at,
    )


async def _wait_for_job_otp(job_id):
    expires_at = timezone.now() + timedelta(seconds=OTP_TIMEOUT_SECONDS)
    marked_pending = await sync_to_async(
        lambda: AutomationJob.objects.filter(
            id=job_id,
            status=AutomationJob.Status.RUNNING,
            cancel_requested=False,
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
    key = otp_redis_key(job_id)
    try:
        while timezone.now() < expires_at:
            code = await redis_client.getdel(key)
            if code is not None:
                resumed = await sync_to_async(
                    lambda: AutomationJob.objects.filter(
                        id=job_id,
                        status=AutomationJob.Status.AWAITING_OTP,
                        cancel_requested=False,
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
                lambda: AutomationJob.objects.filter(id=job_id)
                .values("status", "cancel_requested")
                .first(),
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
def execute_automation_job(self, job_id):
    """Execute one durable job in the Celery automation-worker process."""
    close_old_connections()
    job = None
    try:
        with transaction.atomic():
            job = AutomationJob.objects.select_for_update().get(id=job_id)
            if job.status == AutomationJob.Status.CANCELLED:
                return {"job_id": str(job.id), "status": job.status}
            if job.status == AutomationJob.Status.AWAITING_OTP:
                job.status = AutomationJob.Status.FAILED
                job.error = (
                    "The worker restarted while verification was pending; "
                    "submit a new automation job."
                )
                job.completed_at = timezone.now()
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
                return {"job_id": str(job.id), "status": job.status}
            if job.cancel_requested:
                job.status = AutomationJob.Status.CANCELLED
                job.completed_at = timezone.now()
                job.save(update_fields=["status", "completed_at", "updated_at"])
                return {"job_id": str(job.id), "status": job.status}

            job.status = AutomationJob.Status.RUNNING
            job.started_at = job.started_at or timezone.now()
            job.attempt_count += 1
            if self.request.id:
                job.celery_task_id = self.request.id
            job.save(
                update_fields=[
                    "status",
                    "started_at",
                    "attempt_count",
                    "celery_task_id",
                    "updated_at",
                ]
            )

        from orchestrator import AdapterType, TaskType, UnifiedWorker

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

        async def run_job():
            worker = UnifiedWorker(account_id=job.account_id)

            async def verification_callback(_prompt):
                return await _wait_for_job_otp(job.id)

            try:
                if not await worker.start_session():
                    raise RuntimeError("Could not start the backend automation session.")
                execution_options = dict(job.options)
                if adapter_type == AdapterType.PLAYWRIGHT:
                    execution_options["verification_callback"] = verification_callback
                return await worker.execute(
                    adapter_type,
                    task_type,
                    job.targets,
                    **execution_options,
                )
            finally:
                try:
                    await worker.cleanup()
                finally:
                    await worker.stop_session()

        result = asyncio.run(run_job())
        summary = _result_summary(result, job.targets)
        finished_at = timezone.now()
        with transaction.atomic():
            current = AutomationJob.objects.select_for_update().get(id=job.id)
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
        logger.info(
            "automation job finished",
            extra={
                "job_id": str(job.id),
                "task_id": self.request.id,
                "account_id": job.account_id,
                "action": job.action,
                "attempt": job.attempt_count,
                "status": current.status,
            },
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
            job.status = AutomationJob.Status.RETRYING
            job.error = f"Transient worker failure ({type(exc).__name__}); retry scheduled."
            job.save(update_fields=["status", "error", "updated_at"])
            raise self.retry(
                exc=exc,
                countdown=min(30, 2 ** (self.request.retries + 1)),
                max_retries=2,
            )
        if job is not None:
            _set_job_failure(
                job.id,
                f"Worker execution failed ({type(exc).__name__}).",
            )
        logger.error(
            "automation job execution raised an exception",
            extra={
                "job_id": str(job.id) if job else str(job_id),
                "task_id": self.request.id,
                "account_id": job.account_id if job else None,
                "action": job.action if job else None,
                "error_type": type(exc).__name__,
            },
        )
        raise
    finally:
        close_old_connections()


@shared_task(bind=True, name="api.healthcheck")
def worker_healthcheck(self):
    return {"ok": True, "worker": self.request.hostname, "checked_at": timezone.now().isoformat()}
