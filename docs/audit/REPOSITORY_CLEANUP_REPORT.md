# Repository cleanup report

Branch: `chore/automation-restructure`. Baseline commit: `627daf04fe99419e1b98ec234d9c16e6daca1663`. Uncommitted work in locks, health, logging, runner IPC, and `backend/api/d16_failure_harness.py` was left in place.

Cleanup deleted only modules and scripts with no imports, no URL registration, no Celery registration, no Docker reference, and no migration applied by an installed app.

## Removed

| Path | Category | Evidence | Impact |
| --- | --- | --- | --- |
| `backend/api/v1/` | Duplicate, dead | Not in `INSTALLED_APPS`. No Python import. Models duplicated `account.Proxy` and `account.BotAccount`. Its migration never ran. | None. Live models stay in `backend/account`. |
| `backend/services/` | Dead | Four empty `__init__.py` files. No imports. | None. |
| `backend/api/local_tasks.py` | Dead | No importer. Execute views call Celery only. | None. There is no in-process fallback. |
| `debug_init.py`, `check_db.py`, `test_api.py` | Obsolete scripts | No callers. One-off prints and an unauthenticated POST. | Manual diagnostics are gone. `backend/seed_data.py` remains. |
| `login_error_20261104_073935.html` | Generated debug artifact | Not referenced. | None. |
| `test/playwright/` | Experimental scripts | Not collected by Django. Imports `browser_manager` from the working directory. Several files embedded a real account password. | No regression suite used these files. |
| `backend/account/tests.py`, `backend/analytics/tests.py`, `backend/downloads/tests.py` | Empty stubs | Contained only `from django.test import TestCase` and a comment. | None. Real tests live in `test_*.py` modules. |
| Unused `UnifiedWorker` import in `backend/api/tasks.py` | Dead import | The name was not used. `runner_process.py` constructs `UnifiedWorker`. | None. |
| Unregistered `StartupReconciliationStep` in `backend/api/reconciliation.py` | Duplicate | `backend/config/celery.py` defines and registers the bootstep that calls `reconcile_startup_jobs`. Nothing imported the class in `reconciliation.py`. | Startup reconciliation still runs from the Celery consumer step. |
| `beautifulsoup4` in `requirements.txt` | Unused dependency | No `bs4` or `BeautifulSoup` import. Docker does not install `requirements.txt`. | None for Compose images. |
| `version: '3.8'` in `docker-compose.yml` | Obsolete Compose key | Current Compose ignores it and prints a warning. | Service definitions are unchanged. |

`backend/downloads/tasks.py` still defines `upload_media_to_s3`. `boto3` is now imported inside the task. Celery autodiscovery on the API image no longer fails with `ModuleNotFoundError: boto3`. The backend image does not install `boto3`; the worker image does.

## Kept on purpose

| Component | Classification | Why it stayed |
| --- | --- | --- |
| Spark (`spark_jobs/`, Compose profile `analytics`, `requirements-spark.txt`) | DEPRECATED | No caller, but Compose, a Dockerfile, and a requirements file still install it. |
| Selenium (`automation/selenium_engine/`, `SeleniumAdapter`) | DEPRECATED | `orchestrator/__init__.py` and `UnifiedWorker` import the adapter. The adapter imports `selenium_engine` when that import succeeds. |
| `automation/selenium/` | DEPRECATED | Duplicate of `selenium_engine`. `selenium_engine/fallback_handler.py` imports `automation.selenium` when fallback runs. Deleting it would break that call. |
| Scrapy | DEPRECATED | `ScrapyAdapter` is imported with the orchestrator package. Spiders and `requirements-automation.txt` reference Scrapy. |
| Safety limiter | DEPRECATED | `SafetyAdapter` is imported with the package. `automation/safety/tests/` cover the limiter. The live job map does not call it. |
| Download models, views, and `upload_media_to_s3` | DEPRECATED | URLs are mounted. Migrations exist. Celery autodiscovers the task. No view calls the task or `MediaDownloader`. Job action `download` is a separate path. |
| WebSocket `BotUpdatesConsumer` | DEPRECATED | Mounted in `config.asgi` and `api.routing`. Channels is an installed app. No `group_send` producer. |
| `orchestrator/bot_worker.py` | DEPRECATED | Exported by `orchestrator/__init__.py`. Cookie persistence tests import `BotWorker`. |
| `backend/api/d16_failure_harness.py` | KEEP | Untracked operator harness. Not part of Django discovery. |
| `backend/seed_data.py` | KEEP | Manual sample-data script for the live models. |

Production execution files were not removed: execute views, `job_service`, `execute_automation_job`, account locks, reconciliation function, runner supervisor, runner process, IPC, `UnifiedWorker`, Playwright adapter, and `MediaDownloader`.
