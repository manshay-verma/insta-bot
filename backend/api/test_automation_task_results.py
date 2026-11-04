from contextlib import nullcontext
from types import SimpleNamespace
import sys
import types
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from django.test import SimpleTestCase

from .models import AutomationJob
from .tasks import execute_automation_job


def _orchestrator_module(worker):
    module = types.ModuleType("orchestrator")
    module.__path__ = []

    class AdapterType:
        PLAYWRIGHT = "playwright"
        DOWNLOADER = "downloader"

    class TaskType:
        LIKE_POSTS = "like_posts"
        FOLLOW_USERS = "follow_users"
        UNFOLLOW_USERS = "unfollow_users"
        SCRAPE_PROFILE = "scrape_profile"
        VIEW_STORIES = "view_stories"
        BULK_DOWNLOAD = "bulk_download"
        COMMENT = "comment"

    module.AdapterType = AdapterType
    module.TaskType = TaskType
    module.UnifiedWorker = lambda **kwargs: worker
    return module


def _runner_supervisor_module(worker):
    module = types.ModuleType("orchestrator.runner_supervisor")

    class BrowserRunnerSupervisor:
        def __init__(self, *args, **kwargs):
            self.socket_path = type("SocketPath", (), {"__str__": lambda self: "/tmp/runner.sock"})()

        def start(self):
            return SimpleNamespace(
                runner_id="runner-test",
                pid=123,
                start_ticks=456,
                container_boot_id="boot-test",
                pgid=123,
                profile_path="/tmp/profile",
            )

        async def reconnect(self, timeout_seconds=10):
            return True

        async def execute(self):
            result = await worker.execute("playwright", "follow", ["example"])
            return {
                "ok": True,
                "result": {
                    "success": result.success,
                    "items_processed": result.items_processed,
                    "errors": result.errors,
                    "data": getattr(result, "data", None),
                },
            }

        async def disable_actions(self):
            return True

        async def close(self):
            await worker.cleanup()

    module.BrowserRunnerSupervisor = BrowserRunnerSupervisor
    module.RunnerSupervisorError = RuntimeError
    return module


class AutomationTaskResultTests(SimpleTestCase):
    def _make_job(self):
        return SimpleNamespace(
            id=uuid4(),
            account_id=7,
            action="follow",
            options={},
            targets=["example_user"],
            status=AutomationJob.Status.QUEUED,
            started_at=None,
            attempt_count=0,
            execution_generation=1,
            application_retry_count=0,
            worker_redelivery_count=0,
            recovery_state="none",
            cancel_requested=False,
            save=Mock(),
            refresh_from_db=Mock(),
        )

    def _run_task_with_result(self, result):
        job = self._make_job()
        manager = Mock()
        manager.select_for_update.return_value.get.return_value = job
        worker = SimpleNamespace(
            start_session=AsyncMock(return_value=True),
            execute=AsyncMock(return_value=result),
            cleanup=AsyncMock(),
            stop_session=AsyncMock(),
        )
        with (
            patch("api.tasks.AutomationJob.objects", manager),
            patch("api.tasks.transaction.atomic", return_value=nullcontext()),
            patch("api.tasks.close_old_connections"),
            patch("api.tasks.register_browser_runner", return_value=True),
            patch.dict(
                sys.modules,
                {
                    "orchestrator": _orchestrator_module(worker),
                    "orchestrator.runner_supervisor": _runner_supervisor_module(worker),
                },
            ),
            patch("orchestrator.UnifiedWorker", return_value=worker),
            patch(
                "api.tasks.acquire_account_lock",
                return_value=SimpleNamespace(owner_token="test-owner-token"),
            ),
            patch("api.tasks.release_account_lock", return_value=True),
            patch(
                "api.tasks.resolve_execution_recovery",
                return_value=SimpleNamespace(
                    action="start_new_generation",
                    execution_generation=1,
                    delivery_key="initial:test",
                ),
            ),
        ):
            task_result = execute_automation_job.run(str(job.id))
        return job, task_result

    def test_structured_failure_is_persisted_without_raising(self):
        result = SimpleNamespace(
            success=False,
            items_processed=0,
            errors=["Could not find Follow button"],
        )

        job, task_result = self._run_task_with_result(result)

        self.assertEqual(job.status, AutomationJob.Status.FAILED)
        self.assertEqual(
            job.result["errors"],
            ["Could not find Follow button"],
        )
        self.assertEqual(job.error, "Could not find Follow button")
        self.assertEqual(task_result["status"], AutomationJob.Status.FAILED)
        self.assertFalse(task_result["success"])

    def test_successful_result_is_persisted_as_succeeded(self):
        result = SimpleNamespace(
            success=True,
            items_processed=1,
            errors=[],
        )

        job, task_result = self._run_task_with_result(result)

        self.assertEqual(job.status, AutomationJob.Status.SUCCEEDED)
        self.assertEqual(task_result["status"], AutomationJob.Status.SUCCEEDED)
        self.assertTrue(task_result["success"])

    def test_unexpected_exception_is_raised_and_job_failure_is_written(self):
        job = self._make_job()
        manager = Mock()
        manager.select_for_update.return_value.get.return_value = job

        worker = SimpleNamespace(
            start_session=AsyncMock(return_value=True),
            execute=AsyncMock(side_effect=RuntimeError("worker failed")),
            cleanup=AsyncMock(),
            stop_session=AsyncMock(),
        )

        with (
            patch("api.tasks.AutomationJob.objects", manager),
            patch("api.tasks.transaction.atomic", return_value=nullcontext()),
            patch("api.tasks.close_old_connections"),
            patch("api.tasks.register_browser_runner", return_value=True),
            patch.dict(
                sys.modules,
                {
                    "orchestrator": _orchestrator_module(worker),
                    "orchestrator.runner_supervisor": _runner_supervisor_module(worker),
                },
            ),
            patch("orchestrator.UnifiedWorker", return_value=worker),
            patch(
                "api.tasks.acquire_account_lock",
                return_value=SimpleNamespace(owner_token="test-owner-token"),
            ),
            patch("api.tasks.release_account_lock", return_value=True),
            patch(
                "api.tasks.resolve_execution_recovery",
                return_value=SimpleNamespace(
                    action="start_new_generation",
                    execution_generation=1,
                    delivery_key="initial:test",
                ),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "worker failed"):
                execute_automation_job.run(str(job.id))

        manager.filter.assert_called_once_with(
            id=job.id,
            status__in=(
                AutomationJob.Status.QUEUED,
                AutomationJob.Status.RUNNING,
                AutomationJob.Status.RETRYING,
                AutomationJob.Status.AWAITING_OTP,
                AutomationJob.Status.CANCELLING,
            ),
            execution_generation=1,
        )
        self.assertEqual(
            manager.filter.return_value.update.call_args.kwargs["status"],
            AutomationJob.Status.FAILED,
        )

    def test_missing_job_record_remains_an_explicit_task_failure(self):
        manager = Mock()
        manager.select_for_update.return_value.get.side_effect = (
            AutomationJob.DoesNotExist
        )
        with (
            patch("api.tasks.AutomationJob.objects", manager),
            patch("api.tasks.transaction.atomic", return_value=nullcontext()),
            patch("api.tasks.close_old_connections"),
        ):
            with self.assertRaises(AutomationJob.DoesNotExist):
                execute_automation_job.run(str(uuid4()))

        manager.filter.assert_not_called()
