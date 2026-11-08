# API dependency matrix

Rows are mounted endpoints or endpoint groups. A cell is `yes` only when that request's process, or the Celery task it enqueues before returning, calls the component. An import that the request never reaches is `no`.

| Endpoint | DB | Celery | Orchestrator / runner | Playwright or downloader | Redis | Spark | WebSocket publish |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `POST /api/v1/token/`, refresh, verify | yes | no | no | no | no | no | no |
| `POST /api/v1/register/` | yes | no | no | no | no | no | no |
| `GET/POST /api/v1/settings/` | yes | no | no | no | no | no | no |
| `GET /api/v1/bots/status/` | yes | no | no | no | no | no | no |
| `POST /api/v1/bots/control/` and `/bulk/` | yes | no | no | no | no | no | no |
| `GET /api/v1/health/` | ping | no | no | no | ping | no | no |
| `GET /api/v1/health/detailed/` | yes | inspect only | reads runner identity | no | yes | no | no |
| `GET /api/v1/rate-limits/` | yes | no | no | no | no | no | no |
| `GET /api/v1/system/status/` | yes | no | no | no | no | no | no |
| `GET /api/v1/schedule/upcoming/` | no | no | no | no | no | no | no |
| `POST /api/v1/maintenance/cleanup/` | yes | no | no | no | no | no | no |
| Export create, history, stats, download | yes | no | no | no | no | no | no |
| `POST /api/v1/bot/execute/` and `/async/` | yes | enqueue | later, in the worker | later, in the runner | broker | no | no |
| `GET` job or task status | yes | no | no | no | no | no | no |
| `POST` job verification | yes | no | the runner is already waiting | no | `SET NX` | no | no |
| `POST` job cancel | yes | revoke if still queued | flag only | no | broker for revoke | no | no |
| `/api/v1/proxies/` | yes | no | no | no | no | no | no |
| `/api/v1/accounts/` and health, cookies, session status | yes | no | no | no | no | no | no |
| `/api/v1/sessions/` and `end` | yes | no | no | no | no | no | no |
| `/api/v1/analytics/*` | yes | no | no | no | no | no | no |
| `/api/v1/downloads/*` | yes | no | no | no | no | no | no |
| `ws/updates/` | no | no | no | no | no | no | consumer only |

## How to read the automation column

`POST /api/v1/bot/execute/` is the only client API that schedules browser or downloader work. The HTTP handler's own callees stop at `job_service.submit_automation_job`. The orchestrator is reached only after Celery runs `execute_automation_job`, which starts `orchestrator.runner_process`.

Verification and cancel cooperate with a job that is already running. They do not create a runner.

Account cookie and session-status routes are dependencies of the runner, which calls them with the worker token. A normal dashboard client can also call them, and doing so only updates the database.

## APIs that look connected and are not

| API | What a reader might expect | What the code does |
| --- | --- | --- |
| `POST /api/v1/bots/control/` `start` | Launch the bot | Inserts `Session` |
| `POST /api/v1/bot/execute/async/` | A different execution mode | Same function as `/bot/execute/` |
| `GET /api/v1/schedule/upcoming/` | Celery Beat schedules | Empty list, no model |
| `GET /api/v1/rate-limits/` | `automation/safety` Redis limiter | Constants plus `ActionLog` counts |
| `POST /api/v1/downloads/queue/{id}/process/` | Download media | Inserts `Download(status=pending)` |
| `POST /api/v1/downloads/downloads/bulk/` | Start `MediaDownloader` | Inserts queue rows |
| `ws/updates/` | Live job events | No publisher |
| Any analytics or export route | Spark | ORM only |

No mounted route imports `spark_jobs` or `pyspark`.
