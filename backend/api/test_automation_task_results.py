from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from django.test import SimpleTestCase

from .models import AutomationJob
from .tasks import execute_automation_job


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
            patch("orchestrator.UnifiedWorker", return_value=worker),
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
            patch("orchestrator.UnifiedWorker", return_value=worker),
        ):
            with self.assertRaisesRegex(RuntimeError, "worker failed"):
                execute_automation_job.run(str(job.id))

        manager.filter.assert_called_once_with(id=job.id, status__in=(
            AutomationJob.Status.QUEUED,
            AutomationJob.Status.RUNNING,
            AutomationJob.Status.RETRYING,
            AutomationJob.Status.AWAITING_OTP,
            AutomationJob.Status.CANCELLING,
        ))
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
