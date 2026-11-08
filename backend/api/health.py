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

def _broker_url() -> str:
    from django.conf import settings
    return getattr(settings, "CELERY_BROKER_URL", "redis://redis:6379/0")


def _default_queue_name() -> str:
    from django.conf import settings
    return getattr(settings, "CELERY_TASK_DEFAULT_QUEUE", None) or "celery"


def _redis_client():
    import redis as redis_module
    return redis_module.from_url(
        _broker_url(),
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def _redis_broker_keys() -> Optional[Dict[str, Any]]:
    """
    Key names for the configured Redis transport.

    Queue length is only the default queue, including Kombu priority lists.
    Unacknowledged deliveries live in the transport hash, not in queue length.
    """
    if not _broker_url().startswith(("redis://", "rediss://")):
        return None
    try:
        from kombu.transport.redis import PRIORITY_STEPS, Channel
    except ImportError:
        return None
    queue_name = _default_queue_name()
    queue_keys = []
    for priority in PRIORITY_STEPS:
        if priority:
            queue_keys.append(f"{queue_name}{Channel.sep}{priority}")
        else:
            queue_keys.append(queue_name)
    return {
        "queue": queue_name,
        "queue_keys": queue_keys,
        "unacked_key": Channel.unacked_key,
    }


def _count_list_keys(client, keys: List[str]) -> Optional[int]:
    total = 0
    for key in keys:
        if not client.exists(key):
            continue
        key_type = client.type(key)
        if isinstance(key_type, bytes):
            key_type = key_type.decode("utf-8")
        if key_type != "list":
            return None
        total += int(client.llen(key))
    return total


def _count_hash_key(client, key: str) -> Optional[int]:
    if not client.exists(key):
        return 0
    key_type = client.type(key)
    if isinstance(key_type, bytes):
        key_type = key_type.decode("utf-8")
    if key_type != "hash":
        return None
    return int(client.hlen(key))


def measure_broker_task_counts() -> Dict[str, Any]:
    """
    Measure broker-queued and unacknowledged counts for the Redis transport.

    These counts are not active, reserved, or scheduled tasks. None means the
    count could not be measured. Zero means the transport reported no entries.
    """
    unknown = {
        "broker_queue": _default_queue_name(),
        "broker_queued": None,
        "unacknowledged_tasks": None,
    }
    keys = _redis_broker_keys()
    if keys is None:
        return unknown
    client = None
    try:
        client = _redis_client()
        queued = _count_list_keys(client, keys["queue_keys"])
        unacknowledged = _count_hash_key(client, keys["unacked_key"])
        return {
            "broker_queue": keys["queue"],
            "broker_queued": queued,
            "unacknowledged_tasks": unacknowledged,
        }
    except Exception as exc:
        logger.warning("Broker task counts could not be measured: %s", exc)
        return unknown
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


def _inspect_task_count(payload: Any) -> Optional[int]:
    """Return a count only when every worker reported a list. None is unknown."""
    if not isinstance(payload, dict):
        return None
    total = 0
    for tasks in payload.values():
        if not isinstance(tasks, list):
            return None
        total += len(tasks)
    return total


def check_celery_health() -> Dict[str, Any]:
    """
    Report worker visibility and task states separately.

    Celery inspect supplies active, reserved, and scheduled counts only when a
    worker replies. None means that state was not observed; it is not zero.
    broker_queued is only the default Redis queue, including Kombu priority
    lists. unacknowledged_tasks is the Redis transport's unacked hash.
    Redis queue length is not the set of executing tasks, and a boolean task
    presence check is not task-state visibility.
    """
    broker = measure_broker_task_counts()
    task_states = {
        "active_tasks": None,
        "reserved_tasks": None,
        "scheduled_tasks": None,
        "broker_queued": broker["broker_queued"],
        "unacknowledged_tasks": broker["unacknowledged_tasks"],
        "queue_depth": broker["broker_queued"],
        "broker_queue": broker["broker_queue"],
    }
    try:
        from config.celery import app as celery_app
        inspect = celery_app.control.inspect(timeout=2.0)
        ping_result = inspect.ping()
        if not isinstance(ping_result, dict) or not ping_result:
            return {
                "status": "degraded",
                "reason": "No Celery workers responded to ping",
                "workers": [],
                "worker_count": 0,
                **task_states,
            }

        workers = list(ping_result.keys())
        active_tasks = _inspect_task_count(inspect.active())
        reserved_tasks = _inspect_task_count(inspect.reserved())
        scheduled_tasks = _inspect_task_count(inspect.scheduled())
        partial = any(
            count is None for count in (active_tasks, reserved_tasks, scheduled_tasks)
        )
        return {
            "status": "degraded" if partial else "healthy",
            "reason": "Celery inspect returned a partial task snapshot" if partial else "",
            "workers": workers,
            "worker_count": len(workers),
            "active_tasks": active_tasks,
            "reserved_tasks": reserved_tasks,
            "scheduled_tasks": scheduled_tasks,
            "broker_queued": broker["broker_queued"],
            "unacknowledged_tasks": broker["unacknowledged_tasks"],
            "queue_depth": broker["broker_queued"],
            "broker_queue": broker["broker_queue"],
        }
    except Exception as exc:
        logger.warning("Celery health check failed: %s", exc)
        return {
            "status": "unavailable",
            "error": str(exc),
            "workers": [],
            "worker_count": None,
            **task_states,
        }


# ---------------------------------------------------------------------------
# Browser runner health
# ---------------------------------------------------------------------------

STALE_RUNNER_HEARTBEAT_SECONDS = 600


def _load_runner_process_validator():
    """
    Load the existing runner identity check.

    The backend image does not contain orchestrator and does not share the
    worker process namespace. A failed import means process health is unknown
    here; it must not be reinterpreted as a dead process.
    """
    try:
        from orchestrator.runner_ipc import RunnerIdentity, validate_live_process
    except ImportError as exc:
        logger.warning("Runner process identity validation is unavailable: %s", exc)
        return None, None
    return RunnerIdentity, validate_live_process


def _runner_identity_complete(job) -> bool:
    return all(
        (
            job.runner_pid is not None,
            job.runner_start_ticks is not None,
            job.runner_pgid is not None,
            job.runner_container_boot_id,
            job.runner_profile_path,
            job.runner_id,
        )
    )


def _runner_component_status(runners: List[Dict[str, Any]]) -> str:
    statuses = {runner["runner_status"] for runner in runners}
    if "unknown" in statuses:
        return "unavailable"
    if "dead" in statuses or "stale" in statuses:
        return "degraded"
    return "healthy"


def get_active_runner_health() -> Dict[str, Any]:
    """
    Report runner health from authoritative PostgreSQL rows.

    Process liveness is reported only when the existing runner identity
    validator can run in this process. Otherwise a recorded runner is unknown,
    except a stale heartbeat, which is visible from PostgreSQL alone.
    Health checks do not terminate processes or change job state.
    """
    from .models import AutomationJob

    counts = {
        "runner_count": None,
        "live_count": None,
        "stale_count": None,
        "dead_count": None,
        "unknown_count": None,
    }
    try:
        active_jobs = list(
            AutomationJob.objects.filter(
                status__in=[
                    AutomationJob.Status.RUNNING,
                    AutomationJob.Status.AWAITING_OTP,
                ],
                runner_pid__isnull=False,
            )
        )
    except Exception as exc:
        logger.warning("Runner health: DB query failed: %s", exc)
        return {
            "status": "unavailable",
            "error": str(exc),
            "process_inspection": "unavailable",
            "runners": [],
            **counts,
        }

    runner_identity, validate_live_process = _load_runner_process_validator()
    process_inspection = "available" if validate_live_process is not None else "unavailable"
    now = timezone.now()
    runners = []

    for job in active_jobs:
        heartbeat_age = None
        if job.runner_heartbeat_at:
            heartbeat_age = (now - job.runner_heartbeat_at).total_seconds()
        heartbeat_stale = (
            heartbeat_age is not None and heartbeat_age > STALE_RUNNER_HEARTBEAT_SECONDS
        )
        runner_status = "unknown"
        process_verified = False

        if validate_live_process is not None and _runner_identity_complete(job):
            try:
                identity = runner_identity(
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
                    runner_status = "stale" if heartbeat_stale else "live"
                    process_verified = True
                else:
                    runner_status = "dead"
                    process_verified = True
            except Exception as exc:
                logger.warning("Runner health check failed for job %s: %s", job.id, exc)
                runner_status = "unknown"
        elif heartbeat_stale:
            runner_status = "stale"

        runners.append({
            "job_id": str(job.id),
            "account_id": job.account_id,
            "execution_generation": job.execution_generation,
            "runner_id": str(job.runner_id) if job.runner_id else None,
            "runner_pid": job.runner_pid,
            "job_status": job.status,
            "runner_status": runner_status,
            "process_verified": process_verified,
            "last_heartbeat": job.runner_heartbeat_at.isoformat() if job.runner_heartbeat_at else None,
            "heartbeat_age_seconds": int(heartbeat_age) if heartbeat_age is not None else None,
        })

    return {
        "status": _runner_component_status(runners),
        "process_inspection": process_inspection,
        "runner_count": len(runners),
        "live_count": sum(1 for runner in runners if runner["runner_status"] == "live"),
        "stale_count": sum(1 for runner in runners if runner["runner_status"] == "stale"),
        "dead_count": sum(1 for runner in runners if runner["runner_status"] == "dead"),
        "unknown_count": sum(1 for runner in runners if runner["runner_status"] == "unknown"),
        "runners": runners,
    }


# ---------------------------------------------------------------------------
# Overall health aggregate
# ---------------------------------------------------------------------------

REQUIRED_HEALTH_COMPONENTS = ("database", "redis", "celery", "runners")


def aggregate_component_status(components: Dict[str, Any]) -> str:
    """
    Combine required component statuses.

    Missing component results are unavailable, not healthy and not zero.
    Database or Redis unavailable makes the service unavailable.
    Any other required component that is not healthy makes the result degraded.
    """
    for name in REQUIRED_HEALTH_COMPONENTS:
        component = components.get(name)
        if not isinstance(component, dict) or "status" not in component:
            return "unavailable"

    database_status = components["database"]["status"]
    redis_status = components["redis"]["status"]
    if database_status == "unavailable" or redis_status == "unavailable":
        return "unavailable"
    if database_status != "healthy" or redis_status != "healthy":
        return "degraded"

    for name in REQUIRED_HEALTH_COMPONENTS:
        if components[name]["status"] != "healthy":
            return "degraded"
    return "healthy"


def get_overall_health() -> Dict[str, Any]:
    """
    Aggregate component health check.

    Health check failures MUST NOT trigger recovery actions.
    """
    components = {
        "database": check_database_health(),
        "redis": check_redis_health(),
        "celery": check_celery_health(),
        "runners": get_active_runner_health(),
    }
    return {
        "status": aggregate_component_status(components),
        "checked_at": timezone.now().isoformat(),
        "components": components,
    }

