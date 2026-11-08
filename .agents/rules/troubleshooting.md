---
trigger: always_on
---

# Troubleshooting map

Match the symptom to the file. Do not start by reading Spark, Scrapy, or Selenium.

| Symptom | Look here |
| --- | --- |
| 401 on a dashboard call | JWT header `Bearer`, `REST_FRAMEWORK` auth classes in `backend/config/settings.py` |
| 401 from the runner's API client | `INSTABOT_WORKER_TOKEN` must match on backend and worker. Path must be in `backend/core/auth/worker.py` |
| 409 on execute | Active job constraint or idempotency key reused with a different body (`job_service.py`) |
| 503 on execute | `apply_async` failed. Job row is `failed` with a queue error. Check Redis and that a worker is consuming |
| Job stays `queued` | Celery worker not running, or Compose worker blocked on debugpy `--wait-for-client` |
| Job stays `running` | `AutomationJob.runner_pid`, `runner_ipc_path`, `runner_heartbeat_at`, `AccountBrowserLock` in `backend/api/models.py`. Health: `GET /api/v1/health/detailed/` (`backend/api/health.py`) |
| Job stuck `awaiting_otp` | Redis key from `backend/api/verification.py`. Submit `POST /api/v1/bot/jobs/{id}/verification/` with the same `execution_generation`. Expiry is `verification_expires_at` |
| OTP 409 stale generation | Client sent a generation other than `AutomationJob.execution_generation` |
| Runner exits immediately | `INSTABOT_RUNNER_IPC_SECRET` missing (`orchestrator/runner_ipc.py`). Supervisor error: socket not created |
| Browser profile missing | `INSTABOT_PROFILE_ROOT` and account id in `BrowserRunnerSupervisor.profile_path` |
| Login cannot decrypt password | `account.utils` and `BotAccount.password_encrypted`. Decryption runs inside the runner, not the API request |
| Dashboard says a bot is running but no browser exists | `Session.status=active` from bot control. Browsers exist only for an automation job with runner fields set |
| Download API did nothing | `backend/downloads/views.py` only inserts rows. Media fetch is job action `download` |
| WebSocket stays silent | `backend/api/consumers.py` has no producer. Poll `GET /api/v1/bot/jobs/{id}/` |
| Startup duplicate or lost task | `backend/api/reconciliation.py` and `manage.py reconcile_automation_jobs` |
| Rate limit endpoint disagrees with safety code | The endpoint uses constants in `RateLimitStatusView`, not `automation/safety` |

Logs: `api` and `orchestrator` loggers use `api.logging.StructuredJsonFormatter` and redact sensitive keys. Follow `job_id`, `execution_generation`, and `task_id`.

Database: Postgres when `DB_HOST`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` are set. Otherwise SQLite at `backend/db.sqlite3`. Reconciliation's advisory lock runs only on PostgreSQL.
