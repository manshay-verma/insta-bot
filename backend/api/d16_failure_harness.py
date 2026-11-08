"""Isolated D1.6 failure-injection harness.

This module is not a Django test module and is not imported by Celery.
It refuses to run unless the process is explicitly pointed at the disposable
instabot_d16 database and Redis marker.
"""

import json
import os
import signal
import socket
import subprocess
import sys
import time
import uuid
from datetime import timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

ALLOWED_DATABASE = "instabot_d16"
REDIS_MARKER_KEY = "d16:isolated"
REDIS_MARKER_VALUE = "disposable"


class IsolationError(RuntimeError):
    pass


def _assert_environment():
    if os.environ.get("INSTABOT_D16_ISOLATED") != "1":
        raise IsolationError("INSTABOT_D16_ISOLATED is not set.")
    if os.environ.get("DB_NAME") != ALLOWED_DATABASE:
        raise IsolationError("DB_NAME is not the disposable database.")
    forbidden_db = os.environ.get("INSTABOT_D16_FORBIDDEN_DB_IP", "")
    forbidden_redis = os.environ.get("INSTABOT_D16_FORBIDDEN_REDIS_IP", "")
    db_ip = socket.getaddrinfo(os.environ["DB_HOST"], int(os.environ.get("DB_PORT", "5432")))[0][4][0]
    redis_host = os.environ["CELERY_BROKER_URL"].split("://", 1)[1].split("/")[0].split(":")[0]
    redis_ip = socket.getaddrinfo(redis_host, 6379)[0][4][0]
    if forbidden_db and db_ip == forbidden_db:
        raise IsolationError("Database address matches the live database.")
    if forbidden_redis and redis_ip == forbidden_redis:
        raise IsolationError("Redis address matches the live Redis.")
    return {"db_ip": db_ip, "redis_ip": redis_ip}


def _setup():
    addresses = _assert_environment()
    django.setup()
    from django.conf import settings
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), inet_server_addr()::text")
        database_name, server_addr = cursor.fetchone()
    server_ip = (server_addr or "").split("/", 1)[0]
    if database_name != ALLOWED_DATABASE or server_ip != addresses["db_ip"]:
        raise IsolationError("Django is not connected to the disposable database.")
    import redis

    client = redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2, socket_timeout=2)
    marker = client.get(REDIS_MARKER_KEY)
    if marker != REDIS_MARKER_VALUE.encode("utf-8") and marker != REDIS_MARKER_VALUE:
        raise IsolationError("Redis marker is absent. Refusing to write.")
    client.close()
    return addresses


def _snapshot(job):
    from django.utils import timezone

    from api.models import AccountBrowserLock, ExecutionRecoveryRecord

    job.refresh_from_db()
    lock = AccountBrowserLock.objects.filter(job=job).first()
    records = [
        {
            "failed_generation": record.failed_generation,
            "allocated_generation": record.allocated_generation,
            "recovery_kind": record.recovery_kind,
        }
        for record in ExecutionRecoveryRecord.objects.filter(job=job).order_by("created_at")
    ]
    return {
        "status": job.status,
        "generation": job.execution_generation,
        "recovery_state": job.recovery_state,
        "worker_redelivery_count": job.worker_redelivery_count,
        "runner_pid": job.runner_pid,
        "runner_state": job.runner_state or "",
        "lock_present": lock is not None,
        "lock_generation": None if lock is None else lock.execution_generation,
        "lock_expired": None if lock is None else lock.expires_at <= timezone.now(),
        "recovery_record_count": len(records),
        "recovery_records": records,
        "attempt_count": job.attempt_count,
    }


def _broker_task_names():
    from django.conf import settings
    import redis

    client = redis.from_url(
        settings.CELERY_BROKER_URL,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    names = []
    for raw in client.lrange("celery", 0, -1):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            names.append("unparsed")
            continue
        headers = payload.get("headers") or {}
        names.append(headers.get("task") or "unknown")
    depth = client.llen("celery")
    client.close()
    return {"queue_depth": depth, "task_names": names}


def _create_account(label):
    from django.contrib.auth import get_user_model

    from account.models import BotAccount

    user = get_user_model().objects.create_user(
        username=f"d16-{label}-{uuid.uuid4().hex[:8]}",
        password=uuid.uuid4().hex,
    )
    account = BotAccount.objects.create(
        owner=user,
        username=f"d16_{label}_{uuid.uuid4().hex[:8]}",
        password_encrypted="not-a-real-secret",
    )
    return user, account


def _create_job(user, account, status):
    from api.models import AutomationJob

    return AutomationJob.objects.create(
        user=user,
        account=account,
        action="like",
        targets=["d16-stub-target"],
        status=status,
        execution_generation=0,
    )


def _start_runner(job, account, lock):
    from orchestrator.runner_ipc import validate_live_process
    from orchestrator.runner_supervisor import BrowserRunnerSupervisor

    from api.account_locks import register_browser_runner

    supervisor = BrowserRunnerSupervisor(
        job_id=job.id,
        account_id=account.id,
        execution_generation=job.execution_generation,
        lock_owner_token=lock.owner_token,
        adapter_type="playwright",
        task_type="like",
        targets=["d16-stub-target"],
    )
    identity = supervisor.start()
    register_browser_runner(
        account_id=account.id,
        job_id=job.id,
        owner_token=lock.owner_token,
        execution_generation=job.execution_generation,
        runner=identity,
        runner_ipc_path=str(supervisor.socket_path),
    )
    return supervisor, identity, validate_live_process(identity)


def _kill_process_group(pgid):
    if not pgid:
        return
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        return


def _start_worker(queue="d16-control", log_path="/tmp/d16-celery.log"):
    with open(log_path, "w", encoding="utf-8"):
        pass
    log = open(log_path, "ab")
    process = subprocess.Popen(
        [
            "celery",
            "-A",
            "config",
            "worker",
            "--pool=solo",
            "-Q",
            queue,
            "--loglevel=info",
            "--without-heartbeat",
            "--without-gossip",
            "--without-mingle",
        ],
        cwd="/app/backend",
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    return process, log_path


def _fake_browser_events():
    path = os.environ.get("INSTABOT_FAKE_BROWSER_LOG", "/tmp/d16-fake-browser.jsonl")
    if not os.path.exists(path):
        return []
    events = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                events.append(json.loads(line))
    return events


def _wait_for_job_status(job, status, timeout_seconds=40):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        job.refresh_from_db()
        if job.status == status:
            return True
        time.sleep(0.2)
    return False


def _wait_for_fake_event(event, timeout_seconds=40):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        events = _fake_browser_events()
        if any(item.get("event") == event for item in events):
            return events
        time.sleep(0.1)
    return _fake_browser_events()


def _wait_for_reconciliation(process, log_path, timeout_seconds=40):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None and process.returncode not in (0, None):
            break
        with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        if "reconciliation_completed" in text or "reconciliation_skipped" in text:
            return True
        time.sleep(0.2)
    return False


def _stop_worker(process):
    if process.poll() is None:
        process.send_signal(signal.SIGKILL)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _finish(job):
    from django.utils import timezone

    from api.models import AccountBrowserLock, AutomationJob

    AccountBrowserLock.objects.filter(job=job).delete()
    AutomationJob.objects.filter(id=job.id).exclude(
        status__in=[
            AutomationJob.Status.SUCCEEDED,
            AutomationJob.Status.FAILED,
            AutomationJob.Status.CANCELLED,
        ]
    ).update(
        status=AutomationJob.Status.CANCELLED,
        recovery_state="d16_cleanup",
        completed_at=timezone.now(),
    )


def scenario_worker_termination():
    from django.utils import timezone

    from orchestrator.runner_ipc import validate_live_process

    from api.account_locks import acquire_account_lock
    from api.models import AutomationJob

    user, account = _create_account("worker")
    idle_worker, idle_log = _start_worker()
    idle_ready = _wait_for_reconciliation(idle_worker, idle_log)
    job = _create_job(user, account, AutomationJob.Status.RUNNING)
    job.started_at = timezone.now()
    job.save(update_fields=["started_at", "updated_at"])
    lock = acquire_account_lock(
        account_id=account.id,
        job_id=job.id,
        execution_generation=0,
    )
    supervisor, identity, live_before = _start_runner(job, account, lock)
    before = _snapshot(job)
    failure_at = timezone.now().isoformat()
    _stop_worker(idle_worker)
    runner_live_when_worker_died = validate_live_process(identity)
    _kill_process_group(identity.pgid)
    killed_at = timezone.now().isoformat()
    worker, log_path = _start_worker()
    worker_started = _wait_for_reconciliation(worker, log_path)
    _stop_worker(worker)
    after_first = _snapshot(job)
    broker_after_first = _broker_task_names()
    worker_two, log_path_two = _start_worker()
    second_started = _wait_for_reconciliation(worker_two, log_path_two)
    _stop_worker(worker_two)
    after_second = _snapshot(job)
    broker_after_second = _broker_task_names()
    try:
        supervisor.process.wait(timeout=1)
    except Exception:
        pass
    passed = (
        idle_ready is True
        and before["generation"] == 0
        and live_before is True
        and runner_live_when_worker_died is True
        and after_first["generation"] == 1
        and after_first["recovery_record_count"] == 1
        and after_first["worker_redelivery_count"] == 1
        and after_second["generation"] == 1
        and after_second["recovery_record_count"] == 1
        and broker_after_second["queue_depth"] == broker_after_first["queue_depth"]
        and broker_after_first["queue_depth"] == 1
    )
    result = {
        "scenario": "celery_worker_termination",
        "level": "process",
        "instagram_execute_called": False,
        "worker_reconciliation_observed": idle_ready and worker_started and second_started,
        "failure_at": failure_at,
        "worker_killed_at": killed_at,
        "runner_live_before": live_before,
        "runner_live_when_worker_died": runner_live_when_worker_died,
        "before": before,
        "after_first_recovery": after_first,
        "after_duplicate_worker_start": after_second,
        "broker_after_first": broker_after_first,
        "broker_after_second": broker_after_second,
        "passed": passed,
    }
    _finish(job)
    return result


def scenario_runner_termination():
    from django.utils import timezone

    from orchestrator.runner_ipc import validate_live_process

    from api.account_locks import acquire_account_lock
    from api.models import AutomationJob
    from api.reconciliation import reconcile_startup_jobs

    user, account = _create_account("runner")
    job = _create_job(user, account, AutomationJob.Status.RUNNING)
    job.started_at = timezone.now()
    job.save(update_fields=["started_at", "updated_at"])
    lock = acquire_account_lock(
        account_id=account.id,
        job_id=job.id,
        execution_generation=0,
    )
    supervisor, identity, live_before = _start_runner(job, account, lock)
    second_lock_error = None
    try:
        acquire_account_lock(
            account_id=account.id,
            job_id=job.id,
            execution_generation=0,
            owner_token="different-owner",
        )
    except Exception as exc:
        second_lock_error = type(exc).__name__
    before = _snapshot(job)
    failure_at = timezone.now().isoformat()
    _kill_process_group(identity.pgid)
    live_immediately_after_kill = validate_live_process(identity)
    deadline = time.monotonic() + 2
    live_after_kill = live_immediately_after_kill
    while live_after_kill and time.monotonic() < deadline:
        time.sleep(0.05)
        live_after_kill = validate_live_process(identity)
    broker_before = _broker_task_names()
    recovery = reconcile_startup_jobs(blocking=True)
    after = _snapshot(job)
    broker_after = _broker_task_names()
    passed = (
        live_before is True
        and live_after_kill is False
        and second_lock_error == "AccountLockBusy"
        and after["generation"] == 1
        and after["lock_present"] is False
        and after["recovery_record_count"] == 1
        and broker_after["queue_depth"] == broker_before["queue_depth"] + 1
    )
    result = {
        "scenario": "browser_runner_termination",
        "level": "process",
        "instagram_execute_called": False,
        "failure_at": failure_at,
        "runner_live_before": live_before,
        "runner_live_immediately_after_kill": live_immediately_after_kill,
        "runner_live_after_kill": live_after_kill,
        "second_owner_error": second_lock_error,
        "before": before,
        "recovery_action": next(
            (item.get("action") for item in recovery.get("results", []) if item.get("job_id") == str(job.id)),
            None,
        ),
        "after": after,
        "broker_before": broker_before,
        "broker_after": broker_after,
        "passed": passed,
    }
    try:
        supervisor.process.wait(timeout=1)
    except Exception:
        pass
    _finish(job)
    return result


def scenario_lock_expiry():
    from django.utils import timezone

    from api.account_locks import (
        AccountLockBusy,
        AccountLockOwnershipError,
        acquire_account_lock,
        renew_account_lock,
        validate_account_lock,
    )
    from api.models import AccountBrowserLock, AutomationJob

    user, account = _create_account("lock")
    job = _create_job(user, account, AutomationJob.Status.RUNNING)
    lock = acquire_account_lock(
        account_id=account.id,
        job_id=job.id,
        execution_generation=0,
    )
    before = _snapshot(job)
    AccountBrowserLock.objects.filter(job=job).update(
        expires_at=timezone.now() - timedelta(seconds=5)
    )
    old_renew_error = None
    old_validate_error = None
    try:
        renew_account_lock(
            account_id=account.id,
            job_id=job.id,
            owner_token=lock.owner_token,
            execution_generation=0,
        )
    except AccountLockOwnershipError as exc:
        old_renew_error = type(exc).__name__
    try:
        validate_account_lock(
            account_id=account.id,
            job_id=job.id,
            owner_token=lock.owner_token,
            execution_generation=0,
        )
    except AccountLockOwnershipError as exc:
        old_validate_error = type(exc).__name__
    stale_acquire_error = None
    try:
        acquire_account_lock(
            account_id=account.id,
            job_id=job.id,
            execution_generation=0,
            owner_token=lock.owner_token,
        )
    except AccountLockBusy as exc:
        stale_acquire_error = type(exc).__name__
    job.execution_generation = 1
    job.save(update_fields=["execution_generation", "updated_at"])
    new_lock = acquire_account_lock(
        account_id=account.id,
        job_id=job.id,
        execution_generation=1,
    )
    after = _snapshot(job)
    passed = (
        old_renew_error == "AccountLockOwnershipError"
        and old_validate_error == "AccountLockOwnershipError"
        and stale_acquire_error == "AccountLockBusy"
        and after["generation"] == 1
        and after["lock_generation"] == 1
        and after["lock_expired"] is False
        and new_lock.owner_token != lock.owner_token
    )
    result = {
        "scenario": "account_lock_expiry",
        "level": "integration",
        "before": before,
        "old_generation_renew_error": old_renew_error,
        "old_generation_validate_error": old_validate_error,
        "same_generation_reacquire_error": stale_acquire_error,
        "after_new_generation": after,
        "new_owner_differs": new_lock.owner_token != lock.owner_token,
        "passed": passed,
    }
    _finish(job)
    return result


def scenario_duplicate_delivery():
    from api.account_locks import resolve_execution_recovery
    from api.models import AutomationJob, ExecutionRecoveryRecord

    user, account = _create_account("duplicate")
    job = _create_job(user, account, AutomationJob.Status.QUEUED)
    before = _snapshot(job)
    delivery_key = f"initial:{job.id}:delivery-1"
    first = resolve_execution_recovery(
        job_id=job.id,
        source="initial",
        delivery_key=delivery_key,
    )
    second = resolve_execution_recovery(
        job_id=job.id,
        source="initial",
        delivery_key=delivery_key,
    )
    after = _snapshot(job)
    second_job_error = None
    try:
        AutomationJob.objects.create(
            user=user,
            account=account,
            action="like",
            targets=["d16-stub-target"],
            status=AutomationJob.Status.QUEUED,
        )
    except Exception as exc:
        second_job_error = type(exc).__name__
    passed = (
        before["generation"] == 0
        and first.action == "start_new_generation"
        and first.execution_generation == 1
        and second.action == "duplicate_delivery"
        and second.execution_generation == 1
        and after["generation"] == 1
        and after["recovery_record_count"] == 0
        and ExecutionRecoveryRecord.objects.filter(job=job).count() == 0
        and second_job_error == "IntegrityError"
    )
    result = {
        "scenario": "duplicate_task_delivery",
        "level": "integration",
        "before": before,
        "first_action": first.action,
        "first_generation": first.execution_generation,
        "second_action": second.action,
        "second_generation": second.execution_generation,
        "after": after,
        "second_active_job_error": second_job_error,
        "passed": passed,
    }
    _finish(job)
    return result


def scenario_otp_reconnect():
    from datetime import timedelta

    from django.utils import timezone

    from orchestrator.runner_ipc import validate_live_process

    from api.account_locks import acquire_account_lock
    from api.models import AutomationJob
    from api.reconciliation import reconcile_startup_jobs

    user, account = _create_account("otp")
    job = _create_job(user, account, AutomationJob.Status.AWAITING_OTP)
    job.verification_expires_at = timezone.now() + timedelta(minutes=5)
    job.save(update_fields=["verification_expires_at", "updated_at"])
    lock = acquire_account_lock(
        account_id=account.id,
        job_id=job.id,
        execution_generation=0,
    )
    supervisor, identity, live_before = _start_runner(job, account, lock)
    before = _snapshot(job)
    broker_before = _broker_task_names()
    failure_at = timezone.now().isoformat()
    worker, log_path = _start_worker()
    worker_observed = _wait_for_reconciliation(worker, log_path)
    _stop_worker(worker)
    after_worker_loss = _snapshot(job)
    live_after_worker_loss = validate_live_process(identity)
    broker_after_worker = _broker_task_names()
    _kill_process_group(identity.pgid)
    dead_recovery = reconcile_startup_jobs(blocking=True)
    after_dead = _snapshot(job)
    broker_after_dead = _broker_task_names()
    passed = (
        live_before is True
        and worker_observed is True
        and after_worker_loss["generation"] == 0
        and after_worker_loss["status"] == AutomationJob.Status.AWAITING_OTP
        and live_after_worker_loss is True
        and broker_after_worker["queue_depth"] == broker_before["queue_depth"]
        and after_dead["status"] == AutomationJob.Status.FAILED
        and after_dead["generation"] == 0
        and after_dead["recovery_record_count"] == 0
        and broker_after_dead["queue_depth"] == broker_after_worker["queue_depth"]
    )
    result = {
        "scenario": "otp_reconnect",
        "level": "process",
        "instagram_execute_called": False,
        "failure_at": failure_at,
        "runner_live_before": live_before,
        "runner_live_after_worker_kill": live_after_worker_loss,
        "before": before,
        "after_worker_terminated": after_worker_loss,
        "broker_before": broker_before,
        "broker_after_worker": broker_after_worker,
        "dead_runner_action": dead_recovery["results"][0]["action"] if dead_recovery.get("results") else None,
        "after_dead_runner": after_dead,
        "broker_after_dead_runner": broker_after_dead,
        "passed": passed,
    }
    try:
        supervisor.process.wait(timeout=1)
    except Exception:
        pass
    _finish(job)
    return result


def scenario_redis_baseline():
    from api.models import AutomationJob
    from api.reconciliation import reconcile_startup_jobs

    user, account = _create_account("redis")
    job = _create_job(user, account, AutomationJob.Status.QUEUED)
    job.celery_task_id = ""
    job.save(update_fields=["celery_task_id", "updated_at"])
    before = _snapshot(job)
    recovery = reconcile_startup_jobs(blocking=True)
    after = _snapshot(job)
    broker = _broker_task_names()
    return {
        "scenario": "redis_restart_baseline",
        "level": "process",
        "job_id": str(job.id),
        "before": before,
        "recovery_action": recovery["results"][0]["action"] if recovery.get("results") else None,
        "after": after,
        "broker": broker,
        "passed": after["generation"] == 0 and broker["queue_depth"] >= 1,
    }


def scenario_redis_after():
    from api.models import AutomationJob
    from api.reconciliation import reconcile_startup_jobs

    job = AutomationJob.objects.filter(account__username__startswith="d16_redis_").order_by("-created_at").first()
    if job is None:
        return {"scenario": "redis_restart", "level": "process", "passed": False, "error": "baseline job missing"}
    before = _snapshot(job)
    broker_before = _broker_task_names()
    recovery = reconcile_startup_jobs(blocking=True)
    after = _snapshot(job)
    broker_after = _broker_task_names()
    passed = (
        before["generation"] == after["generation"] == 0
        and before["status"] == AutomationJob.Status.QUEUED
        and broker_before["queue_depth"] == 0
        and broker_after["queue_depth"] == 1
        and after["recovery_record_count"] == 0
    )
    result = {
        "scenario": "redis_restart",
        "level": "process",
        "postgres_authoritative": True,
        "before": before,
        "broker_immediately_after_restart": broker_before,
        "recovery_action": recovery["results"][0]["action"] if recovery.get("results") else None,
        "after_reconcile": after,
        "broker_after_reconcile": broker_after,
        "passed": passed,
    }
    _finish(job)
    return result


def scenario_database_down():
    from django.db import connection
    from django.db.utils import OperationalError

    from api.reconciliation import reconcile_startup_jobs

    connection.close()
    error_name = None
    try:
        reconcile_startup_jobs(blocking=True)
    except OperationalError as exc:
        error_name = type(exc).__name__
    except Exception as exc:
        error_name = type(exc).__name__
    return {
        "scenario": "postgresql_unavailable",
        "level": "process",
        "exception": error_name,
        "passed": error_name == "OperationalError",
    }


def scenario_database_restored():
    from django.db import connection

    from api.models import AutomationJob
    from api.reconciliation import reconcile_startup_jobs

    connection.close()
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    job = (
        AutomationJob.objects.filter(account__username__startswith="d16_redis_")
        .order_by("-created_at")
        .first()
    )
    if job is None:
        return {"scenario": "postgresql_restored", "level": "process", "passed": False, "error": "seed job missing"}
    before = _snapshot(job)
    recovery = reconcile_startup_jobs(blocking=True)
    after = _snapshot(job)
    return {
        "scenario": "postgresql_restored",
        "level": "process",
        "before": before,
        "after_reconcile": after,
        "reconciled_jobs": recovery.get("reconciled_jobs"),
        "passed": before["generation"] == after["generation"] and after["status"] == before["status"],
    }


def _prepare_dead_runner_job(label):
    from django.utils import timezone

    from api.models import AutomationJob

    AutomationJob.objects.exclude(
        status__in=[
            AutomationJob.Status.SUCCEEDED,
            AutomationJob.Status.FAILED,
            AutomationJob.Status.CANCELLED,
        ]
    ).update(status=AutomationJob.Status.CANCELLED, recovery_state="cancelled")
    user, account = _create_account(label)
    job = _create_job(user, account, AutomationJob.Status.RUNNING)
    job.started_at = timezone.now()
    job.runner_pid = 999999
    job.runner_pgid = 999999
    job.runner_state = "running"
    job.save(update_fields=["started_at", "runner_pid", "runner_pgid", "runner_state", "updated_at"])
    return job


def scenario_consume_recovery():
    from api.reconciliation import reconcile_startup_jobs
    from api.tasks import execute_automation_job

    if os.environ.get("INSTABOT_FAKE_BROWSER") != "1":
        return {"scenario": "recovered_task_execution", "level": "process", "passed": False, "error": "fake browser disabled"}
    log_path = os.environ.get("INSTABOT_FAKE_BROWSER_LOG", "/tmp/d16-fake-browser.jsonl")
    if os.path.exists(log_path):
        os.remove(log_path)
    job = _prepare_dead_runner_job("consume")
    before = _snapshot(job)
    recovery = reconcile_startup_jobs(blocking=True)
    published = _snapshot(job)
    broker_published = _broker_task_names()
    worker, worker_log = _start_worker(queue="celery", log_path="/d16-logs/consumer.log")
    try:
        from api.models import AutomationJob

        consumed = _wait_for_job_status(job, AutomationJob.Status.SUCCEEDED)
        after_execution = _snapshot(job)
        events_after_execution = _fake_browser_events()
        execute_automation_job.delay(
            job_id=str(job.id),
            execution_generation=job.execution_generation,
            delivery_reason="worker_redelivery",
            recovery_delivery_key=job.recovery_delivery_key,
        )
        time.sleep(3)
        job.refresh_from_db()
        after_duplicate = _snapshot(job)
        events_after_duplicate = _fake_browser_events()
    finally:
        _stop_worker(worker)
    completed = [item for item in events_after_duplicate if item.get("event") == "completed" and item.get("job_id") == str(job.id)]
    passed = (
        before["generation"] == 0
        and published["generation"] == 1
        and published["recovery_record_count"] == 1
        and broker_published["queue_depth"] >= 1
        and "api.execute_automation_job" in broker_published["task_names"]
        and consumed is True
        and after_execution["status"] == "succeeded"
        and after_execution["generation"] == 1
        and after_execution["recovery_record_count"] == 1
        and after_duplicate["generation"] == 1
        and after_duplicate["recovery_record_count"] == 1
        and after_duplicate["status"] == "succeeded"
        and len(completed) == 1
    )
    result = {
        "scenario": "recovered_task_execution",
        "level": "process",
        "browser": "fake_browser",
        "instagram_contacted": False,
        "worker_log": worker_log,
        "published_action": next(
            (item.get("action") for item in recovery.get("results", []) if item.get("job_id") == str(job.id)),
            None,
        ),
        "before": before,
        "after_publish": published,
        "broker_after_publish": broker_published,
        "after_execution": after_execution,
        "fake_events_after_execution": events_after_execution,
        "after_duplicate_delivery": after_duplicate,
        "fake_events_after_duplicate": events_after_duplicate,
        "passed": passed,
    }
    _finish(job)
    return result


def scenario_interrupt_browser():
    from orchestrator.runner_ipc import validate_live_process
    from orchestrator.runner_ipc import RunnerIdentity

    from api.models import AutomationJob
    from api.reconciliation import reconcile_startup_jobs

    if os.environ.get("INSTABOT_FAKE_BROWSER") != "1":
        return {"scenario": "browser_execution_interruption", "level": "process", "passed": False, "error": "fake browser disabled"}
    hold_path = os.environ.get("INSTABOT_FAKE_BROWSER_HOLD", "")
    if not hold_path:
        return {"scenario": "browser_execution_interruption", "level": "process", "passed": False, "error": "hold path missing"}
    log_path = os.environ.get("INSTABOT_FAKE_BROWSER_LOG", "/tmp/d16-fake-browser.jsonl")
    if os.path.exists(log_path):
        os.remove(log_path)
    with open(hold_path, "w", encoding="utf-8") as handle:
        handle.write("wait")
    job = _prepare_dead_runner_job("interrupt")
    before = _snapshot(job)
    first_recovery = reconcile_startup_jobs(blocking=True)
    after_publish = _snapshot(job)
    worker, worker_log = _start_worker(queue="celery", log_path="/d16-logs/interrupt-consumer.log")
    entered = _wait_for_fake_event("entered")
    job.refresh_from_db()
    reached_browser = _snapshot(job)
    runner_live = False
    if job.runner_pid and job.runner_start_ticks and job.runner_pgid and job.runner_container_boot_id and job.runner_id:
        runner_live = validate_live_process(RunnerIdentity(
            runner_id=str(job.runner_id),
            pid=job.runner_pid,
            start_ticks=job.runner_start_ticks,
            container_boot_id=job.runner_container_boot_id,
            pgid=job.runner_pgid,
            execution_generation=job.execution_generation,
            job_id=str(job.id),
            profile_path=job.runner_profile_path,
        ))
    interrupted_generation = job.execution_generation
    interrupted_pid = job.runner_pid
    _stop_worker(worker)
    _kill_process_group(job.runner_pgid)
    with open(hold_path, "w", encoding="utf-8") as handle:
        handle.write("release")
    after_kill = _snapshot(job)
    replacement, replacement_log = _start_worker(queue="celery", log_path="/d16-logs/interrupt-recovery.log")
    try:
        completed = _wait_for_job_status(job, AutomationJob.Status.SUCCEEDED, timeout_seconds=45)
        after_recovery = _snapshot(job)
        from api.tasks import execute_automation_job

        execute_automation_job.delay(
            job_id=str(job.id),
            execution_generation=job.execution_generation,
            delivery_reason="worker_redelivery",
            recovery_delivery_key=job.recovery_delivery_key,
        )
        time.sleep(3)
        after_duplicate = _snapshot(job)
    finally:
        _stop_worker(replacement)
    events = _fake_browser_events()
    job_events = [item for item in events if item.get("job_id") == str(job.id)]
    completed_events = [item for item in job_events if item.get("event") == "completed"]
    entered_generations = [item.get("execution_generation") for item in job_events if item.get("event") == "entered"]
    completed_generations = [item.get("execution_generation") for item in completed_events]
    passed = (
        before["generation"] == 0
        and after_publish["generation"] == 1
        and after_publish["recovery_record_count"] == 1
        and any(item.get("event") == "entered" and item.get("execution_generation") == interrupted_generation for item in job_events)
        and runner_live is True
        and interrupted_pid is not None
        and after_kill["status"] == AutomationJob.Status.RUNNING
        and after_kill["generation"] == interrupted_generation
        and completed is True
        and after_recovery["status"] == AutomationJob.Status.SUCCEEDED
        and after_recovery["generation"] == interrupted_generation + 1
        and after_recovery["recovery_record_count"] == 2
        and after_duplicate["generation"] == after_recovery["generation"]
        and after_duplicate["recovery_record_count"] == 2
        and after_duplicate["status"] == AutomationJob.Status.SUCCEEDED
        and completed_generations == [interrupted_generation + 1]
        and interrupted_generation in entered_generations
        and interrupted_generation not in completed_generations
    )
    result = {
        "scenario": "browser_execution_interruption",
        "level": "process",
        "browser": "fake_browser",
        "instagram_contacted": False,
        "first_recovery_action": next(
            (item.get("action") for item in first_recovery.get("results", []) if item.get("job_id") == str(job.id)),
            None,
        ),
        "before": before,
        "after_publish": after_publish,
        "reached_browser_stage": reached_browser,
        "runner_live_at_browser_stage": runner_live,
        "interrupted_generation": interrupted_generation,
        "after_runner_and_worker_killed": after_kill,
        "after_recovery_execution": after_recovery,
        "after_duplicate_delivery": after_duplicate,
        "fake_events": job_events,
        "consumer_log": worker_log,
        "recovery_log": replacement_log,
        "entered": bool(entered),
        "passed": passed,
    }
    _finish(job)
    return result


COMMANDS = {
    "isolate": lambda: {"isolated": True, **_setup()},
    "migrate": None,
    "worker": scenario_worker_termination,
    "runner": scenario_runner_termination,
    "lock": scenario_lock_expiry,
    "duplicate": scenario_duplicate_delivery,
    "otp": scenario_otp_reconnect,
    "redis-baseline": scenario_redis_baseline,
    "redis-after": scenario_redis_after,
    "db-down": scenario_database_down,
    "db-restored": scenario_database_restored,
    "consume-recovery": scenario_consume_recovery,
    "interrupt-browser": scenario_interrupt_browser,
}


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "migrate":
        _assert_environment()
        django.setup()
        from django.core.management import call_command

        call_command("migrate", interactive=False, verbosity=0)
        import redis
        from django.conf import settings

        client = redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2, socket_timeout=2)
        client.set(REDIS_MARKER_KEY, REDIS_MARKER_VALUE)
        client.close()
        print(json.dumps({"migrated": True, "database": ALLOWED_DATABASE}))
        return
    if command == "remark-redis":
        _assert_environment()
        django.setup()
        import redis
        from django.conf import settings

        client = redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2, socket_timeout=2)
        client.set(REDIS_MARKER_KEY, REDIS_MARKER_VALUE)
        client.close()
        print(json.dumps({"redis_remarked": True}))
        return
    if command == "db-down":
        if os.environ.get("INSTABOT_D16_ISOLATED") != "1" or os.environ.get("DB_NAME") != ALLOWED_DATABASE:
            raise IsolationError("Disposable database was not selected.")
        django.setup()
        print(json.dumps(scenario_database_down(), default=str))
        return
    if command not in COMMANDS:
        raise SystemExit("unknown command")
    _setup()
    print(json.dumps(COMMANDS[command](), default=str))


if __name__ == "__main__":
    try:
        main()
    except IsolationError as exc:
        print(json.dumps({"isolated": False, "error": str(exc)}))
        raise SystemExit(2)
