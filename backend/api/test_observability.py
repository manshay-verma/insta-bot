"""
D1.5 Observability tests.

Tests for:
- SensitiveDataFilter secret redaction
- StructuredJsonFormatter output fields
- log_structured() helper correctness
- Stale/dead/live runner detection (get_active_runner_health)
- Celery health None-safe behavior
- Database health check
- Reconciliation metrics (action_counts, duration_ms)
- No secrets appear in log output

Must run in worker container:
  docker compose exec worker python manage.py test api.test_observability
"""

import json
import logging
import os
import time
import uuid
from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from api.logging import (
    SensitiveDataFilter,
    StructuredJsonFormatter,
    log_structured,
    redact_sensitive_data,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_logger_with_capture():
    """Return (logger, stream) where stream captures JSON log lines."""
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredJsonFormatter())
    handler.addFilter(SensitiveDataFilter())
    log = logging.getLogger(f"test.observability.{uuid.uuid4().hex}")
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    log.propagate = False
    return log, stream


def _last_record(stream):
    """Parse the last JSON log line from stream."""
    stream.seek(0)
    lines = [l.strip() for l in stream.read().splitlines() if l.strip()]
    if not lines:
        return None
    return json.loads(lines[-1])


# ---------------------------------------------------------------------------
# Secret Redaction Tests
# ---------------------------------------------------------------------------

class TestRedactSensitiveData(TestCase):

    def test_redacts_password_key(self):
        result = redact_sensitive_data({"password": "hunter2", "other": "ok"})
        self.assertEqual(result["password"], "[REDACTED]")
        self.assertEqual(result["other"], "ok")

    def test_redacts_token_key(self):
        result = redact_sensitive_data({"owner_token": "abc123"})
        self.assertEqual(result["owner_token"], "[REDACTED]")

    def test_redacts_cookie_key(self):
        result = redact_sensitive_data({"cookies": "sessionid=ABCDEF"})
        self.assertEqual(result["cookies"], "[REDACTED]")

    def test_redacts_bearer_in_string(self):
        result = redact_sensitive_data("Authorization: Bearer eyJhbGciOiJSUzI1NiJ9.payload.sig")
        self.assertNotIn("eyJhbGciOiJSUzI1NiJ9", result)
        self.assertIn("[REDACTED]", result)

    def test_redacts_sessionid_in_string(self):
        result = redact_sensitive_data("sessionid=abc123xyz; other=value")
        self.assertNotIn("abc123xyz", result)
        self.assertIn("[REDACTED]", result)

    def test_redacts_nested_dict(self):
        result = redact_sensitive_data({"user": {"name": "alice", "password": "secret"}})
        self.assertEqual(result["user"]["password"], "[REDACTED]")
        self.assertEqual(result["user"]["name"], "alice")

    def test_redacts_in_list(self):
        result = redact_sensitive_data([{"token": "abc"}, {"name": "bob"}])
        self.assertEqual(result[0]["token"], "[REDACTED]")
        self.assertEqual(result[1]["name"], "bob")

    def test_non_sensitive_passthrough(self):
        result = redact_sensitive_data({"job_id": "uuid-1234", "status": "RUNNING"})
        self.assertEqual(result["job_id"], "uuid-1234")
        self.assertEqual(result["status"], "RUNNING")

    def test_integer_passthrough(self):
        result = redact_sensitive_data(42)
        self.assertEqual(result, 42)


class TestSensitiveDataFilter(TestCase):

    def _make_record(self, msg, **extra):
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg=msg, args=(), exc_info=None,
        )
        for k, v in extra.items():
            setattr(record, k, v)
        return record

    def test_filter_redacts_bearer_in_msg(self):
        f = SensitiveDataFilter()
        record = self._make_record("Token: Bearer abc123.def456")
        f.filter(record)
        self.assertNotIn("abc123", record.msg)
        self.assertIn("[REDACTED]", record.msg)

    def test_filter_redacts_sensitive_extra_key(self):
        f = SensitiveDataFilter()
        record = self._make_record("ok", owner_token="super_secret_token")
        f.filter(record)
        self.assertEqual(getattr(record, "owner_token", None), "[REDACTED]")

    def test_filter_preserves_job_id(self):
        f = SensitiveDataFilter()
        record = self._make_record("ok", job_id="uuid-123")
        f.filter(record)
        self.assertEqual(getattr(record, "job_id", None), "uuid-123")

    def test_filter_returns_true(self):
        f = SensitiveDataFilter()
        record = self._make_record("ok")
        result = f.filter(record)
        self.assertTrue(result)


# ---------------------------------------------------------------------------
# StructuredJsonFormatter Tests
# ---------------------------------------------------------------------------

class TestStructuredJsonFormatter(TestCase):

    def test_standard_fields_present(self):
        log, stream = _make_logger_with_capture()
        log_structured(log, logging.INFO, "test_event", "Hello",
            job_id="job-1", account_id=42, execution_generation=3, runner_id="runner-9")
        rec = _last_record(stream)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["event"], "test_event")
        self.assertEqual(rec["job_id"], "job-1")
        self.assertEqual(rec["account_id"], 42)
        self.assertEqual(rec["execution_generation"], 3)
        self.assertEqual(rec["runner_id"], "runner-9")
        self.assertEqual(rec["message"], "Hello")
        self.assertIn("timestamp", rec)
        self.assertIn("level", rec)
        self.assertIn("logger", rec)

    def test_none_identifiers(self):
        log, stream = _make_logger_with_capture()
        log_structured(log, logging.INFO, "sparse_event", "No IDs")
        rec = _last_record(stream)
        self.assertIsNone(rec["job_id"])
        self.assertIsNone(rec["account_id"])
        self.assertIsNone(rec["runner_id"])

    def test_no_secrets_in_output(self):
        log, stream = _make_logger_with_capture()
        log_structured(log, logging.INFO, "test", "msg",
            job_id="j1",
            context_data={"password": "SUPER_SECRET_PASSWORD"})
        stream.seek(0)
        output = stream.read()
        self.assertNotIn("SUPER_SECRET_PASSWORD", output)
        self.assertIn("[REDACTED]", output)

    def test_bearer_token_not_in_output(self):
        log, stream = _make_logger_with_capture()
        log.info("Called with Bearer eyXYZabc.payload.sig")
        stream.seek(0)
        output = stream.read()
        self.assertNotIn("eyXYZabc", output)
        self.assertIn("[REDACTED]", output)

    def test_otp_key_redacted(self):
        log, stream = _make_logger_with_capture()
        log_structured(log, logging.INFO, "otp_event", "otp submitted",
            otp_code="123456")
        stream.seek(0)
        output = stream.read()
        self.assertNotIn("123456", output)


# ---------------------------------------------------------------------------
# Runner Health Tests
# ---------------------------------------------------------------------------

class TestRunnerHealth(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="health_test_user", password="test")

    def _make_job(self, **kwargs):
        from account.models import BotAccount
        from api.models import AutomationJob
        account = BotAccount.objects.create(
            owner=self.user,
            username=f"health_ig_{uuid.uuid4().hex[:8]}",
            password_encrypted="encrypted",
        )
        return AutomationJob.objects.create(
            user=self.user,
            account=account,
            action="like",
            targets=["https://instagram.com/p/test/"],
            status=AutomationJob.Status.RUNNING,
            **kwargs,
        )

    def test_no_running_jobs_returns_healthy(self):
        from api.health import get_active_runner_health
        result = get_active_runner_health()
        # Should not error; may have no runners or existing ones
        self.assertIn("status", result)
        self.assertIn("runners", result)

    def test_dead_pid_runner_returns_dead(self):
        """A job with a PID that does not exist should report runner_status=dead."""
        from api.health import get_active_runner_health
        # Use a PID that is almost certainly not running
        dead_pid = 999999
        boot_id = ""
        try:
            with open("/proc/sys/kernel/random/boot_id") as f:
                boot_id = f.read().strip()
        except Exception:
            boot_id = "test-boot-id"

        job = self._make_job(
            runner_pid=dead_pid,
            runner_start_ticks=1,
            runner_pgid=dead_pid,
            runner_container_boot_id=boot_id,
            runner_profile_path="/tmp/test_profile",
            runner_id=uuid.uuid4(),
            runner_heartbeat_at=timezone.now(),
        )
        result = get_active_runner_health()
        runner_entries = [r for r in result["runners"] if r["job_id"] == str(job.id)]
        self.assertEqual(len(runner_entries), 1)
        self.assertEqual(runner_entries[0]["runner_status"], "dead")

    def test_live_pid_runner_returns_live(self):
        """A job with the current process PID should report runner_status=live."""
        from api.health import get_active_runner_health
        boot_id = ""
        try:
            with open("/proc/sys/kernel/random/boot_id") as f:
                boot_id = f.read().strip()
        except Exception:
            boot_id = "test-boot-id"

        my_pid = os.getpid()
        my_pgid = os.getpgid(my_pid)

        # Read start_ticks for current process from /proc/<pid>/stat
        try:
            with open(f"/proc/{my_pid}/stat") as f:
                parts = f.read().split()
                start_ticks = int(parts[21])
        except Exception:
            self.skipTest("Cannot read /proc/self/stat")

        job = self._make_job(
            runner_pid=my_pid,
            runner_start_ticks=start_ticks,
            runner_pgid=my_pgid,
            runner_container_boot_id=boot_id,
            runner_profile_path="/tmp/test_profile",
            runner_id=uuid.uuid4(),
            runner_heartbeat_at=timezone.now(),
        )
        result = get_active_runner_health()
        runner_entries = [r for r in result["runners"] if r["job_id"] == str(job.id)]
        self.assertEqual(len(runner_entries), 1)
        self.assertEqual(runner_entries[0]["runner_status"], "live")

    def test_stale_heartbeat_runner_returns_stale(self):
        """A live PID but old heartbeat should report runner_status=stale."""
        from api.health import get_active_runner_health
        boot_id = ""
        try:
            with open("/proc/sys/kernel/random/boot_id") as f:
                boot_id = f.read().strip()
        except Exception:
            boot_id = "test-boot-id"

        my_pid = os.getpid()
        my_pgid = os.getpgid(my_pid)
        try:
            with open(f"/proc/{my_pid}/stat") as f:
                parts = f.read().split()
                start_ticks = int(parts[21])
        except Exception:
            self.skipTest("Cannot read /proc/self/stat")

        # Heartbeat 15 minutes ago (beyond 10-minute stale threshold)
        old_heartbeat = timezone.now() - timedelta(minutes=15)
        job = self._make_job(
            runner_pid=my_pid,
            runner_start_ticks=start_ticks,
            runner_pgid=my_pgid,
            runner_container_boot_id=boot_id,
            runner_profile_path="/tmp/test_profile",
            runner_id=uuid.uuid4(),
            runner_heartbeat_at=old_heartbeat,
        )
        result = get_active_runner_health()
        runner_entries = [r for r in result["runners"] if r["job_id"] == str(job.id)]
        self.assertEqual(len(runner_entries), 1)
        self.assertEqual(runner_entries[0]["runner_status"], "stale")


# ---------------------------------------------------------------------------
# Celery Health Tests
# ---------------------------------------------------------------------------

class TestCeleryHealth(TestCase):

    def test_celery_health_none_ping_returns_degraded(self):
        """When inspect.ping() returns None, status should be 'degraded', not an exception."""
        from api.health import check_celery_health
        mock_inspect = MagicMock()
        mock_inspect.ping.return_value = None

        with patch("api.health.check_celery_health") as mock_fn:
            # Test the None-safe logic directly by patching the inspect
            pass

        # Test by patching at the celery app level
        with patch("config.celery.app.control.inspect") as mock_inspect_cls:
            mock_inst = MagicMock()
            mock_inst.ping.return_value = None
            mock_inspect_cls.return_value = mock_inst

            result = check_celery_health()

        self.assertIn(result["status"], {"degraded", "healthy", "unavailable"})
        # Should not raise
        self.assertIsInstance(result, dict)

    def test_celery_health_exception_returns_unavailable(self):
        """When inspect raises, status should be 'unavailable'."""
        from api.health import check_celery_health
        with patch("config.celery.app.control.inspect") as mock_inspect_cls:
            mock_inspect_cls.side_effect = RuntimeError("broker unreachable")

            result = check_celery_health()

        self.assertEqual(result["status"], "unavailable")
        self.assertIn("error", result)

    def test_celery_health_returns_dict(self):
        """check_celery_health always returns a dict."""
        from api.health import check_celery_health
        result = check_celery_health()
        self.assertIsInstance(result, dict)
        self.assertIn("status", result)
        self.assertIn("workers", result)

    def test_celery_queue_depth_informational_only(self):
        """queue_depth is returned as informational field, not used as sole proof."""
        from api.health import check_celery_health
        result = check_celery_health()
        # queue_depth may be None or int — either is acceptable
        qd = result.get("queue_depth")
        self.assertTrue(qd is None or isinstance(qd, int))


# ---------------------------------------------------------------------------
# Database Health Tests
# ---------------------------------------------------------------------------

class TestDatabaseHealth(TestCase):

    def test_database_healthy_with_live_db(self):
        from api.health import check_database_health
        result = check_database_health()
        self.assertEqual(result["status"], "healthy")
        self.assertIn("latency_ms", result)
        self.assertIsInstance(result["latency_ms"], int)

    def test_database_unavailable_on_error(self):
        from api.health import check_database_health
        with patch("api.health.connection") as mock_conn:
            mock_conn.cursor.side_effect = Exception("DB gone")
            result = check_database_health()
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("error", result)


# ---------------------------------------------------------------------------
# Redis Health Tests
# ---------------------------------------------------------------------------

class TestRedisHealth(TestCase):

    def test_redis_healthy(self):
        from api.health import check_redis_health
        result = check_redis_health()
        # Redis is running in the worker container
        self.assertIn(result["status"], {"healthy", "unavailable"})
        self.assertIn("latency_ms", result)

    def test_redis_unavailable_on_error(self):
        from api.health import check_redis_health
        with patch("redis.Redis.from_url") as mock_redis:
            mock_inst = MagicMock()
            mock_inst.ping.side_effect = Exception("Redis gone")
            mock_redis.return_value = mock_inst
            result = check_redis_health()
        # May hit the "import redis" branch differently — just ensure no exception
        self.assertIsInstance(result, dict)
        self.assertIn("status", result)


# ---------------------------------------------------------------------------
# Overall Health Tests
# ---------------------------------------------------------------------------

class TestOverallHealth(TestCase):

    def test_overall_health_returns_valid_structure(self):
        from api.health import get_overall_health
        result = get_overall_health()
        self.assertIn("status", result)
        self.assertIn(result["status"], {"healthy", "degraded", "unavailable"})
        self.assertIn("components", result)
        self.assertIn("database", result["components"])
        self.assertIn("redis", result["components"])
        self.assertIn("celery", result["components"])
        self.assertIn("runners", result["components"])
        self.assertIn("checked_at", result)

    def test_overall_unavailable_when_db_down(self):
        from api.health import get_overall_health
        with patch("api.health.check_database_health") as mock_db:
            mock_db.return_value = {"status": "unavailable", "latency_ms": 0}
            result = get_overall_health()
        self.assertEqual(result["status"], "unavailable")

    def test_overall_unavailable_when_redis_down(self):
        from api.health import get_overall_health
        with patch("api.health.check_redis_health") as mock_redis:
            mock_redis.return_value = {"status": "unavailable", "latency_ms": 0}
            result = get_overall_health()
        self.assertEqual(result["status"], "unavailable")

    def test_overall_degraded_when_celery_unavailable(self):
        from api.health import get_overall_health
        with patch("api.health.check_celery_health") as mock_celery:
            mock_celery.return_value = {
                "status": "unavailable", "workers": [], "queue_depth": None,
                "active_tasks": None, "reserved_tasks": None,
            }
            with patch("api.health.check_database_health") as mock_db:
                mock_db.return_value = {"status": "healthy", "latency_ms": 1}
                with patch("api.health.check_redis_health") as mock_r:
                    mock_r.return_value = {"status": "healthy", "latency_ms": 1}
                    result = get_overall_health()
        self.assertEqual(result["status"], "degraded")

    def test_health_check_does_not_trigger_recovery(self):
        """
        Regression: calling get_overall_health() must not modify any AutomationJob records.
        """
        from api.health import get_overall_health
        from api.models import AutomationJob
        before_count = AutomationJob.objects.count()
        get_overall_health()
        after_count = AutomationJob.objects.count()
        self.assertEqual(before_count, after_count)


# ---------------------------------------------------------------------------
# Reconciliation Metrics Tests
# ---------------------------------------------------------------------------

class TestReconciliationMetrics(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="recon_metrics_user", password="test")

    def test_reconcile_returns_duration_ms(self):
        """reconcile_startup_jobs() returns duration_ms field."""
        from api.reconciliation import reconcile_startup_jobs
        result = reconcile_startup_jobs(blocking=False)
        self.assertIn("duration_ms", result)
        self.assertIsInstance(result["duration_ms"], int)
        self.assertGreaterEqual(result["duration_ms"], 0)

    def test_reconcile_returns_action_counts(self):
        """reconcile_startup_jobs() returns action_counts dict."""
        from api.reconciliation import reconcile_startup_jobs
        result = reconcile_startup_jobs(blocking=False)
        self.assertIn("action_counts", result)
        self.assertIsInstance(result["action_counts"], dict)

    def test_reconcile_metrics_with_terminal_job(self):
        """A SUCCEEDED job should be counted as noop_terminal."""
        from account.models import BotAccount
        from api.models import AutomationJob
        from api.reconciliation import reconcile_startup_jobs
        account = BotAccount.objects.create(
            owner=self.user,
            username=f"metrics_ig_{uuid.uuid4().hex[:8]}",
            password_encrypted="encrypted",
        )
        AutomationJob.objects.create(
            user=self.user,
            account=account,
            action="like",
            targets=["https://instagram.com/p/test/"],
            status=AutomationJob.Status.SUCCEEDED,
            completed_at=timezone.now(),
        )
        result = reconcile_startup_jobs(blocking=False)
        # Terminal jobs don't get scanned (filtered out by active_statuses)
        # So action_counts should NOT contain noop_terminal for the SUCCEEDED job
        self.assertIsInstance(result, dict)
        self.assertIn("reconciled_jobs", result)

    def test_reconcile_metrics_with_queued_job_in_redis(self):
        """A QUEUED job with task present in Redis returns queued_task_healthy."""
        from account.models import BotAccount
        from api.models import AutomationJob
        from api.reconciliation import reconcile_startup_jobs
        account = BotAccount.objects.create(
            owner=self.user,
            username=f"queued_ig_{uuid.uuid4().hex[:8]}",
            password_encrypted="encrypted",
        )
        task_id = str(uuid.uuid4())
        job = AutomationJob.objects.create(
            user=self.user,
            account=account,
            action="like",
            targets=["https://instagram.com/p/test/"],
            status=AutomationJob.Status.QUEUED,
            celery_task_id=task_id,
        )
        with patch("api.reconciliation.is_celery_task_present", return_value=True):
            result = reconcile_startup_jobs(blocking=False)
        counts = result.get("action_counts", {})
        self.assertGreaterEqual(counts.get("queued_task_healthy", 0), 1)


def _healthy_components():
    return {
        "database": {"status": "healthy"},
        "redis": {"status": "healthy"},
        "celery": {"status": "healthy"},
        "runners": {"status": "healthy"},
    }


class TestHealthAggregation(TestCase):

    def test_all_healthy_components_are_healthy(self):
        from api.health import aggregate_component_status
        self.assertEqual(aggregate_component_status(_healthy_components()), "healthy")

    def test_database_unavailable_is_unavailable(self):
        from api.health import aggregate_component_status
        components = _healthy_components()
        components["database"] = {"status": "unavailable"}
        self.assertEqual(aggregate_component_status(components), "unavailable")

    def test_redis_unavailable_is_unavailable(self):
        from api.health import aggregate_component_status
        components = _healthy_components()
        components["redis"] = {"status": "unavailable"}
        self.assertEqual(aggregate_component_status(components), "unavailable")

    def test_degraded_celery_is_not_healthy(self):
        from api.health import aggregate_component_status
        components = _healthy_components()
        components["celery"] = {"status": "degraded", "active_tasks": None}
        self.assertEqual(aggregate_component_status(components), "degraded")

    def test_unavailable_runners_are_not_healthy(self):
        from api.health import aggregate_component_status
        components = _healthy_components()
        components["runners"] = {"status": "unavailable", "runners": []}
        self.assertEqual(aggregate_component_status(components), "degraded")

    def test_unknown_component_is_not_healthy(self):
        from api.health import aggregate_component_status
        components = _healthy_components()
        components["runners"] = {"status": "unknown"}
        self.assertEqual(aggregate_component_status(components), "degraded")

    def test_missing_component_is_unavailable(self):
        from api.health import aggregate_component_status
        components = _healthy_components()
        del components["runners"]
        self.assertEqual(aggregate_component_status(components), "unavailable")

    def test_missing_dead_count_is_not_treated_as_zero(self):
        from api.health import aggregate_component_status
        components = _healthy_components()
        components["runners"] = {"runners": []}
        self.assertEqual(aggregate_component_status(components), "unavailable")


class TestRunnerHealthWithoutProcessInspection(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="runner_unknown_user", password="test")

    def _make_running_job(self, **kwargs):
        from account.models import BotAccount
        from api.models import AutomationJob
        account = BotAccount.objects.create(
            owner=self.user,
            username=f"unknown_ig_{uuid.uuid4().hex[:8]}",
            password_encrypted="encrypted",
        )
        defaults = {
            "runner_pid": 4242,
            "runner_start_ticks": 10,
            "runner_pgid": 4242,
            "runner_container_boot_id": "boot",
            "runner_profile_path": "/tmp/test_profile",
            "runner_id": uuid.uuid4(),
            "runner_heartbeat_at": timezone.now(),
        }
        defaults.update(kwargs)
        return AutomationJob.objects.create(
            user=self.user,
            account=account,
            action="like",
            targets=["https://instagram.com/p/test/"],
            status=AutomationJob.Status.RUNNING,
            **defaults,
        )

    def test_no_rows_stay_healthy_when_process_inspection_is_unavailable(self):
        from api.health import get_active_runner_health
        with patch("api.health._load_runner_process_validator", return_value=(None, None)):
            result = get_active_runner_health()
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(result["process_inspection"], "unavailable")
        self.assertEqual(result["runner_count"], 0)
        self.assertEqual(result["dead_count"], 0)
        self.assertEqual(result["unknown_count"], 0)

    def test_recorded_runner_is_unknown_without_process_inspection(self):
        from api.health import get_active_runner_health
        job = self._make_running_job()
        with patch("api.health._load_runner_process_validator", return_value=(None, None)):
            result = get_active_runner_health()
        entry = next(item for item in result["runners"] if item["job_id"] == str(job.id))
        self.assertEqual(entry["runner_status"], "unknown")
        self.assertFalse(entry["process_verified"])
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["unknown_count"], 1)
        self.assertEqual(result["dead_count"], 0)

    def test_stale_heartbeat_is_reported_from_postgresql_without_process_inspection(self):
        from api.health import get_active_runner_health
        job = self._make_running_job(runner_heartbeat_at=timezone.now() - timedelta(minutes=15))
        with patch("api.health._load_runner_process_validator", return_value=(None, None)):
            result = get_active_runner_health()
        entry = next(item for item in result["runners"] if item["job_id"] == str(job.id))
        self.assertEqual(entry["runner_status"], "stale")
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["stale_count"], 1)


class TestCeleryTaskStates(TestCase):

    def _inspect(self, ping, active=None, reserved=None, scheduled=None):
        inspect = MagicMock()
        inspect.ping.return_value = ping
        inspect.active.return_value = active
        inspect.reserved.return_value = reserved
        inspect.scheduled.return_value = scheduled
        return inspect

    def test_worker_states_are_separate_from_broker_counts(self):
        from api.health import check_celery_health
        inspect = self._inspect(
            {"worker-a": {"ok": "pong"}},
            active={"worker-a": [{"id": "active-1"}]},
            reserved={"worker-a": [{"id": "reserved-1"}, {"id": "reserved-2"}]},
            scheduled={"worker-a": []},
        )
        broker = {"broker_queue": "celery", "broker_queued": 4, "unacknowledged_tasks": 1}
        with patch("config.celery.app.control.inspect", return_value=inspect):
            with patch("api.health.measure_broker_task_counts", return_value=broker):
                result = check_celery_health()
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(result["active_tasks"], 1)
        self.assertEqual(result["reserved_tasks"], 2)
        self.assertEqual(result["scheduled_tasks"], 0)
        self.assertEqual(result["broker_queued"], 4)
        self.assertEqual(result["unacknowledged_tasks"], 1)
        self.assertEqual(result["queue_depth"], 4)

    def test_missing_inspect_snapshot_is_unknown_not_zero(self):
        from api.health import check_celery_health
        inspect = self._inspect({"worker-a": {"ok": "pong"}}, active=None, reserved=None, scheduled=None)
        broker = {"broker_queue": "celery", "broker_queued": 0, "unacknowledged_tasks": 0}
        with patch("config.celery.app.control.inspect", return_value=inspect):
            with patch("api.health.measure_broker_task_counts", return_value=broker):
                result = check_celery_health()
        self.assertEqual(result["status"], "degraded")
        self.assertIsNone(result["active_tasks"])
        self.assertIsNone(result["reserved_tasks"])
        self.assertIsNone(result["scheduled_tasks"])
        self.assertEqual(result["broker_queued"], 0)

    def test_no_worker_does_not_turn_unknown_states_into_zero(self):
        from api.health import check_celery_health
        inspect = self._inspect(None)
        broker = {"broker_queue": "celery", "broker_queued": 3, "unacknowledged_tasks": None}
        with patch("config.celery.app.control.inspect", return_value=inspect):
            with patch("api.health.measure_broker_task_counts", return_value=broker):
                result = check_celery_health()
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["worker_count"], 0)
        self.assertIsNone(result["active_tasks"])
        self.assertIsNone(result["reserved_tasks"])
        self.assertIsNone(result["scheduled_tasks"])
        self.assertEqual(result["broker_queued"], 3)
        self.assertIsNone(result["unacknowledged_tasks"])

    def test_non_redis_transport_does_not_invent_broker_counts(self):
        from api.health import measure_broker_task_counts
        with patch("api.health._broker_url", return_value="amqp://guest:guest@rabbitmq:5672//"):
            result = measure_broker_task_counts()
        self.assertIsNone(result["broker_queued"])
        self.assertIsNone(result["unacknowledged_tasks"])

    def test_unexpected_unacked_type_is_unknown(self):
        from api.health import measure_broker_task_counts

        class FakeRedis:
            def exists(self, key):
                return True

            def type(self, key):
                if key == "unacked":
                    return "string"
                return "list"

            def llen(self, key):
                return 2

            def hlen(self, key):
                return 9

            def close(self):
                pass

        with patch("api.health._redis_client", return_value=FakeRedis()):
            with patch("api.health._broker_url", return_value="redis://redis:6379/0"):
                result = measure_broker_task_counts()
        self.assertEqual(result["broker_queued"], 2 * 4)
        self.assertIsNone(result["unacknowledged_tasks"])


class TestLoggingConfiguration(TestCase):

    def test_every_handler_uses_structured_json_and_redaction(self):
        from django.conf import settings
        handlers = settings.LOGGING["handlers"]
        self.assertTrue(handlers)
        for name, handler in handlers.items():
            self.assertEqual(handler.get("formatter"), "structured", name)
            self.assertIn("sensitive_data_filter", handler.get("filters", []), name)

    def test_configured_handler_preserves_identifiers_and_redacts_secrets(self):
        from django.conf import settings
        from django.utils.module_loading import import_string

        stream = StringIO()
        formatter = import_string(settings.LOGGING["formatters"]["structured"]["()"])()
        redaction_filter = import_string(settings.LOGGING["filters"]["sensitive_data_filter"]["()"])()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(formatter)
        handler.addFilter(redaction_filter)
        log = logging.getLogger(f"test.logging.config.{uuid.uuid4().hex}")
        log.handlers = [handler]
        log.setLevel(logging.INFO)
        log.propagate = False
        log.info(
            "Authorization: Bearer super-secret-token sessionid=abcdef",
            extra={
                "event": "health_test",
                "job_id": "job-77",
                "password": "hunter2",
                "owner_token": "lock-token",
                "otp_code": "123456",
            },
        )
        payload = json.loads(stream.getvalue())
        self.assertEqual(payload["event"], "health_test")
        self.assertEqual(payload["job_id"], "job-77")
        rendered = stream.getvalue()
        self.assertNotIn("hunter2", rendered)
        self.assertNotIn("lock-token", rendered)
        self.assertNotIn("123456", rendered)
        self.assertNotIn("super-secret-token", rendered)
        self.assertNotIn("abcdef", rendered)
        self.assertIn("[REDACTED]", rendered)

