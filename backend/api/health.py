"""
D1.5 Health Monitoring — component-level health checks for PostgreSQL, Redis,
Celery worker, and browser runners.

Health check failures MUST NOT trigger recovery actions.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from django.db import connection
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Database health
# ---------------------------------------------------------------------------

def check_database_health() -> Dict[str, Any]:
    """
    Returns {"status": "healthy"|"unavailable", "latency_ms": N}.
    Never raises; always returns a dict.
    """
    start = time.monotonic()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        latency_ms = int((time.monotonic() - start) * 1000)
        return {"status": "healthy", "latency_ms": latency_ms}
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.warning("Database health check failed: %s", exc)
        return {"status": "unavailable", "latency_ms": latency_ms, "error": str(exc)}


# ---------------------------------------------------------------------------
# Redis health
# ---------------------------------------------------------------------------

def check_redis_health() -> Dict[str, Any]:
    """
    Returns {"status": "healthy"|"unavailable", "latency_ms": N}.
    Never raises; always returns a dict.
    """
    start = time.monotonic()
    try:
        import redis as redis_module
        from django.conf import settings
        client = redis_module.from_url(
            getattr(settings, "CELERY_BROKER_URL", "redis://redis:6379/0"),
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        latency_ms = int((time.monotonic() - start) * 1000)
        return {"status": "healthy", "latency_ms": latency_ms}
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.warning("Redis health check failed: %s", exc)
        return {"status": "unavailable", "latency_ms": latency_ms, "error": str(exc)}


# ---------------------------------------------------------------------------
# Celery worker health
# ---------------------------------------------------------------------------

def _get_redis_queue_depth() -> Optional[int]:
    """
    Returns the informational queue depth from Redis for the default 'celery' queue.
    Not proof of task execution state — informational only.
    """
    try:
        import redis as redis_module
        from django.conf import settings
        client = redis_module.from_url(
            getattr(settings, "CELERY_BROKER_URL", "redis://redis:6379/0"),
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        return client.llen("celery")
    except Exception:
        return None


def check_celery_health() -> Dict[str, Any]:
    """
    Returns worker availability, active/reserved task counts via Celery inspect.
    Uses inspect(timeout=2.0) with None-safe fallback.

    Status:
      - "healthy": ping succeeded
      - "degraded": ping returned None (no workers responded) or partial info
      - "unavailable": inspect raised an exception

    IMPORTANT: Does not use Redis queue length alone as proof a task is or is not
    executing. Active and reserved counts come from Celery inspect if available.
    """
    try:
        from config.celery import app as celery_app
        inspect = celery_app.control.inspect(timeout=2.0)

        ping_result = inspect.ping()
        if ping_result is None:
            # No workers responded — degraded (not unavailable, worker may be starting)
            queue_depth = _get_redis_queue_depth()
            return {
                "status": "degraded",
                "reason": "No Celery workers responded to ping",
                "workers": [],
                "queue_depth": queue_depth,  # informational only
                "active_tasks": None,
                "reserved_tasks": None,
            }

        workers = list(ping_result.keys())

        # Gather active and reserved task counts — None-safe
        active = inspect.active()
        reserved = inspect.reserved()

        active_count = (
            sum(len(v) for v in active.values()) if active else 0
        )
        reserved_count = (
            sum(len(v) for v in reserved.values()) if reserved else 0
        )

        queue_depth = _get_redis_queue_depth()

        return {
            "status": "healthy",
            "workers": workers,
            "worker_count": len(workers),
            "queue_depth": queue_depth,  # informational only
            "active_tasks": active_count,
            "reserved_tasks": reserved_count,
        }

    except Exception as exc:
        logger.warning("Celery health check failed: %s", exc)
        return {
            "status": "unavailable",
            "error": str(exc),
            "workers": [],
            "queue_depth": None,
            "active_tasks": None,
            "reserved_tasks": None,
        }


# ---------------------------------------------------------------------------
# Browser runner health
# ---------------------------------------------------------------------------

def get_active_runner_health() -> Dict[str, Any]:
    """
    Returns health status for all jobs with an active browser runner (RUNNING or AWAITING_OTP
    with runner_pid set).

    Uses validate_live_process from orchestrator.runner_ipc.
    Health check failures do NOT trigger recovery.

    Runner status values:
      - "live": process exists and matches identity
      - "dead": process gone or identity mismatch
      - "stale": heartbeat too old (> 10 minutes without update)
    """
    # Deferred import to avoid AppRegistryNotReady at module level
    from .models import AutomationJob

    STALE_THRESHOLD_SECONDS = 600  # 10 minutes

    try:
        from orchestrator.runner_ipc import RunnerIdentity, validate_live_process
    except ImportError as exc:
        logger.warning("Cannot import runner_ipc for health check: %s", exc)
        return {"status": "unavailable", "error": str(exc), "runners": []}

    now = timezone.now()
    runners = []

    try:
        active_jobs = AutomationJob.objects.filter(
            status__in=[
                AutomationJob.Status.RUNNING,
                AutomationJob.Status.AWAITING_OTP,
            ],
            runner_pid__isnull=False,
        ).select_related()
    except Exception as exc:
        logger.warning("Runner health: DB query failed: %s", exc)
        return {"status": "unavailable", "error": str(exc), "runners": []}

    for job in active_jobs:
        runner_status = "dead"
        heartbeat_age = None

        if job.runner_heartbeat_at:
            heartbeat_age = (now - job.runner_heartbeat_at).total_seconds()

        if (
            job.runner_pid is not None
            and job.runner_start_ticks is not None
            and job.runner_pgid is not None
            and job.runner_container_boot_id
            and job.runner_profile_path
            and job.runner_id
        ):
            try:
                identity = RunnerIdentity(
                    runner_id=str(job.runner_id),
                    pid=job.runner_pid,
                    start_ticks=job.runner_start_ticks,
                    container_boot_id=job.runner_container_boot_id,
                    pgid=job.runner_pgid,
                    execution_generation=job.execution_generation,
                    job_id=str(job.id),
                    profile_path=job.runner_profile_path,
                )
                if validate_live_process(identity):
                    if heartbeat_age is not None and heartbeat_age > STALE_THRESHOLD_SECONDS:
                        runner_status = "stale"
                    else:
                        runner_status = "live"
                else:
                    runner_status = "dead"
            except Exception as exc:
                logger.warning(
                    "Runner health check failed for job %s: %s", job.id, exc
                )
                runner_status = "dead"

        runners.append({
            "job_id": str(job.id),
            "account_id": job.account_id,
            "execution_generation": job.execution_generation,
            "runner_id": str(job.runner_id) if job.runner_id else None,
            "runner_pid": job.runner_pid,
            "job_status": job.status,
            "runner_status": runner_status,
            "last_heartbeat": job.runner_heartbeat_at.isoformat() if job.runner_heartbeat_at else None,
            "heartbeat_age_seconds": int(heartbeat_age) if heartbeat_age is not None else None,
        })

    stale_count = sum(1 for r in runners if r["runner_status"] == "stale")
    dead_count = sum(1 for r in runners if r["runner_status"] == "dead")

    return {
        "status": "healthy" if dead_count == 0 and stale_count == 0 else "degraded",
        "runner_count": len(runners),
        "live_count": sum(1 for r in runners if r["runner_status"] == "live"),
        "stale_count": stale_count,
        "dead_count": dead_count,
        "runners": runners,
    }


# ---------------------------------------------------------------------------
# Overall health aggregate
# ---------------------------------------------------------------------------

def get_overall_health() -> Dict[str, Any]:
    """
    Aggregate component health check.

    Status rules:
      - "healthy":   DB healthy, Redis healthy, Celery not unavailable, no dead/stale runners
      - "degraded":  Celery degraded, or any stale/dead runner, but DB + Redis healthy
      - "unavailable": DB or Redis unavailable

    Health check failures MUST NOT trigger recovery actions.
    """
    db = check_database_health()
    redis_h = check_redis_health()
    celery_h = check_celery_health()
    runner_h = get_active_runner_health()

    db_ok = db["status"] == "healthy"
    redis_ok = redis_h["status"] == "healthy"
    celery_ok = celery_h["status"] in {"healthy", "degraded"}  # degraded ≠ broken
    runner_ok = runner_h.get("dead_count", 0) == 0 and runner_h.get("stale_count", 0) == 0

    if not db_ok or not redis_ok:
        overall = "unavailable"
    elif not celery_ok or not runner_ok:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "checked_at": timezone.now().isoformat(),
        "components": {
            "database": db,
            "redis": redis_h,
            "celery": celery_h,
            "runners": runner_h,
        },
    }

