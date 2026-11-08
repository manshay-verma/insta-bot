---
trigger: always_on
---

# File map for agents

Open these files first. Do not scan the whole tree until the map misses the symbol.

## HTTP and jobs

| Question | File |
| --- | --- |
| Mounted prefixes | `backend/config/urls.py` |
| Dashboard, health, exports | `backend/api/urls.py`, `backend/api/views.py`, `backend/api/health.py` |
| Execute, status, OTP, cancel | `backend/api/bot_execute.py` |
| Job body validation | `backend/api/job_serializers.py` |
| Queue a job | `backend/api/job_service.py` |
| Run a job | `backend/api/tasks.py` (`execute_automation_job`) |
| Locks, generation fence, runner identity | `backend/api/account_locks.py` |
| OTP Redis key | `backend/api/verification.py` |
| Lost-worker repair | `backend/api/reconciliation.py`, `backend/api/management/commands/reconcile_automation_jobs.py` |
| Celery app and startup hook | `backend/config/celery.py` |
| Settings, DB, Redis, JWT, logging | `backend/config/settings.py` |
| Worker token allow-list | `backend/core/auth/worker.py` |
| Error JSON | `backend/core/exceptions.py` |
| Job and lock models | `backend/api/models.py` |
| Accounts, proxies, sessions | `backend/account/models.py`, `backend/account/views.py`, `backend/account/urls.py` |
| Analytics | `backend/analytics/views.py`, `backend/analytics/models.py` |
| Download tables (not the downloader) | `backend/downloads/views.py`, `backend/downloads/urls.py` |

The uninstalled duplicate app `backend/api/v1/` was removed. Account models live only in `backend/account/models.py`.

## Runner and automation

| Question | File |
| --- | --- |
| Subprocess and Unix socket client | `orchestrator/runner_supervisor.py` |
| Socket server and `UnifiedWorker` construction | `orchestrator/runner_process.py` |
| IPC HMAC and pid checks | `orchestrator/runner_ipc.py` |
| Adapter choice inside the runner | `orchestrator/unified_worker.py` |
| Calls back into Django | `orchestrator/api_client.py` |
| Action logs | `orchestrator/callbacks.py` |
| Cookies | `orchestrator/cookie_sync.py` |
| Browser actions | `orchestrator/adapters/playwright_adapter.py` |
| Browser implementation | `automation/playwright_engine/browser_manager.py` |
| Job action `download` | `orchestrator/adapters/downloader_adapter.py`, `automation/downloader/media_downloader.py` |

The runner process is the only construction site for `UnifiedWorker`.

## Not on the live job path

- `orchestrator/bot_worker.py` — manual Playwright worker
- `orchestrator/adapters/selenium_adapter.py`, `scrapy_adapter.py`, `safety_adapter.py`
- `automation/selenium/`, `automation/selenium_engine/`, `automation/scrapy_project/`, `automation/safety/`
- `spark_jobs/` — deprecated, Compose profile `analytics`, no caller
- `backend/downloads/tasks.py` — `upload_media_to_s3` has no caller; module stays because Celery autodiscovers the installed app
- `backend/api/consumers.py` — WebSocket with no publisher; route stays mounted

## Tests that describe current behavior

- `backend/api/test_automation_jobs.py`
- `backend/api/test_automation_task_results.py`
- `backend/api/test_account_locks.py`
- `backend/api/test_browser_runner.py`
- `backend/api/test_startup_reconciliation.py`
- `backend/api/test_observability.py`
- `backend/account/test_session_management.py`
