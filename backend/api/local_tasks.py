"""
Local in-process task runner (Celery fallback).

Purpose:
- Provide async execution for automation endpoints even when Celery/Redis
  are not configured or not running.
- Store task status/results in memory (dev only).
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


_executor = ThreadPoolExecutor(max_workers=4)


@dataclass
class LocalTaskRecord:
    status: str  # PENDING | STARTED | SUCCESS | FAILURE
    result: Any = None
    error: Optional[str] = None


_tasks: Dict[str, LocalTaskRecord] = {}
_lock = threading.Lock()


def submit(coro_factory: Callable[[], "asyncio.Future[Any]"]) -> str:
    """
    Submit an async coroutine factory to run in a background thread.

    Returns:
        task_id: str
    """
    task_id = str(uuid.uuid4())
    with _lock:
        _tasks[task_id] = LocalTaskRecord(status="PENDING")

    def _runner():
        # Playwright uses asyncio subprocesses; on Windows that requires Proactor loop.
        try:
            import sys
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass

        with _lock:
            _tasks[task_id].status = "STARTED"
        try:
            result = asyncio.run(coro_factory())
            with _lock:
                _tasks[task_id].status = "SUCCESS"
                _tasks[task_id].result = result
        except Exception as e:  # pragma: no cover (best effort)
            with _lock:
                _tasks[task_id].status = "FAILURE"
                _tasks[task_id].error = str(e)

    _executor.submit(_runner)
    return task_id


def get(task_id: str) -> Optional[LocalTaskRecord]:
    with _lock:
        return _tasks.get(task_id)

