# Final repository review

## 1. Health

The production path is intact: execute API, `job_service`, `AutomationJob`, Celery `api.execute_automation_job`, generation fencing, `AccountBrowserLock`, `orchestrator.runner_process`, `UnifiedWorker`, Playwright actions, `MediaDownloader`, and job polling.

The tree is smaller where code had no caller. Optional engines that Docker, adapters, or tests still import were marked deprecated and left in place. A developer should start at `docs/README.md` and `.agents/rules/source-map.md`, and treat `docs/legacy/` plus root notes such as `AUTOMATION_ARCHITECTURE_MAP.md` as historical.

## 2. Files reviewed

313 files remained after cleanup, excluding `.git`, `__pycache__`, and `frontend/node_modules`. 170 of those are Python files. Review covered Django apps, orchestrator, automation, Spark, Compose, requirements, tests, and the agent rules. `frontend/node_modules` was not read file by file.

## 3. Files deleted

- Uninstalled duplicate app `backend/api/v1/`
- Empty `backend/services/`
- `backend/api/local_tasks.py`
- `debug_init.py`, `check_db.py`, `test_api.py`
- `login_error_20261104_073935.html`
- `test/playwright/` (15 manual scripts)
- Three empty `tests.py` stubs

## 4. Files retained

The live API, Celery task, locks, reconciliation function, runner, Playwright engine, media downloader, account and analytics apps, download app, and the deprecated Spark, Selenium, Scrapy, safety, WebSocket, and S3 task code.

## 5. Dead code removed

The unused `UnifiedWorker` import and the unregistered copy of `StartupReconciliationStep`. The registered bootstep remains in `backend/config/celery.py`.

## 6. Duplicate implementations removed

The duplicate account models under `backend/api/v1/accounts/` and the duplicate unregistered Celery bootstep. The duplicate Selenium tree `automation/selenium/` was not removed because `selenium_engine` fallback imports it.

## 7. Tests deleted

The `test/playwright/` scripts and three empty Django stubs. Reasons are in `docs/audit/TEST_SUITE_REVIEW.md`. They were experimental or empty, and several Playwright scripts stored a plaintext password.

## 8. Tests retained

201 `def test_` methods across the modules listed in the test review. They cover locks, fencing, jobs, OTP, reconciliation, runner IPC, sessions, Playwright helpers, the downloader, and the safety limiter.

## 9. Dependencies removed

`beautifulsoup4` from `requirements.txt` only. No image installs that file. No other package was removed.

## 10. Unused components retained

Spark, Selenium, Scrapy, the safety limiter, the download-queue API, the S3 task, and the WebSocket consumer are DEPRECATED. Evidence is in `docs/audit/REPOSITORY_CLEANUP_REPORT.md`.

## 11. Production architecture verification

URL reverse in the backend container:

- `/api/v1/bot/execute/`
- `/api/v1/bot/execute/async/`
- `/api/v1/bots/control/`
- `/api/v1/bot/jobs/<uuid>/`

Celery tasks discovered after the lazy `boto3` import:

- `api.execute_automation_job`
- `api.healthcheck`
- `config.celery.debug_task`
- `downloads.tasks.upload_media_to_s3`

`manage.py check` reported no issues.

## 12. Validation results

| Check | Result |
| --- | --- |
| `manage.py check` in `insta-bot-backend-1` | No issues |
| URL reverse for execute, async execute, bot control, job status | Resolved |
| Celery autodiscovery on the backend image | Succeeds. Before the lazy import it raised `No module named 'boto3'`. |
| `api.test_automation_jobs` and `api.test_account_locks` | 40 tests, OK |
| `api.test_instagram_targets`, `api.test_startup_reconciliation`, `api.test_automation_task_results` in the worker image | 32 tests, OK |
| `docker compose config` | Valid after removing the obsolete `version` key |
| Observability, browser-runner, session, Playwright engine, safety, and downloader unit tests | Not executed |

The host has no `inst-bot-venv` on `PATH`. Tests ran inside the existing Compose backend container and a one-off worker container.

## 13. Remaining risks

- `INSTABOT_RUNNER_IPC_SECRET` is still absent from `docker-compose.yml`. A real runner exits until it is set.
- The Compose worker command still waits for a debugpy client, so the default worker does not consume the queue until a debugger attaches.
- `upload_media_to_s3` still has no caller. Running it on the backend image will fail at the `boto3` import inside the function.
- Selenium, Scrapy, and safety code can still be constructed if a future caller passes those adapter types. They are not selected by `execute_automation_job`.
- Root markdown files (`AUTOMATION_ARCHITECTURE_MAP.md`, `FULL_README.md`, `README_INTERVIEW.md`, `RESUME_PROJECT_NOTES.md`) still describe older layouts.

## 14. Recommended next steps

- Add the runner IPC secret to the worker environment before expecting live browsers.
- Decide whether the deprecated engines should be deleted in a later change once Compose profiles and adapter imports are removed together.
- Add the missing tests listed in `docs/audit/TEST_SUITE_REVIEW.md`.
- Point new readers at `docs/README.md` and ignore `docs/legacy/` for behavior questions.
