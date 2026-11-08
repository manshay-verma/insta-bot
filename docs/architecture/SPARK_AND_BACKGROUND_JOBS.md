# Spark and background jobs

Spark is not part of request handling. Background work that actually runs is Celery, plus the browser-runner subprocess that the automation task starts.

## Why Spark is in the repository

`spark_jobs/` holds example analytics scripts:

| File | Intended work | Output coded in the file | Who calls it |
| --- | --- | --- | --- |
| `spark_jobs/spark_app.py` | Build a session and, if uncommented, aggregate hashtags | MongoDB via the Mongo Spark connector | Nobody. `__main__` creates a session and stops it. `run_hashtag_analysis` is commented out |
| `spark_jobs/batch/hashtag_trending.py` | Count hashtags | MongoDB `append` | Nobody |
| `spark_jobs/ml/recommendation_als.py` | ALS recommendations from a ratings dataframe | `s3a://instabot-analytics/recommendations/als_latest/` | Nobody |
| `spark_jobs/streaming/activity_monitor.py` | 5-minute activity windows | Spark console sink | Nobody. The function requires the caller to pass a streaming dataframe |

A repository search for `spark_jobs`, `pyspark`, and `SparkSession` outside `spark_jobs/` hits only `docker-compose.yml`, which volume-mounts the directory into the `spark-master` service. That service is behind the Compose profile `analytics`. It is not started with the default `db`, `redis`, `backend`, `worker`, and `frontend` services. No API, Celery task, management command, or orchestrator module submits a Spark application.

`spark_app.create_spark_session` ends in `.get_create()`. The PySpark builder method is `getOrCreate()`. Invoking this helper would raise `AttributeError` before any read or write.

MongoDB and the Node service are also profile-gated (`optional-data`). Django settings do not configure a Mongo connection. Analytics that the dashboard reads come from `analytics.DailyAnalytics`, `ActionLog`, and `UserBehavior` in the Django database.

## Celery tasks that exist

Defined tasks:

| Task | Module | Called by | Effect |
| --- | --- | --- | --- |
| `api.execute_automation_job` | `backend/api/tasks.py` | `submit_automation_job`, and reconciliation when it requeues a lost job | Account lock, runner process, Playwright or downloader, job result |
| `api.healthcheck` | `backend/api/tasks.py` | No scheduler in the repo | Reconcile expired account locks and return worker hostname |
| `config.celery.debug_task` | `backend/config/celery.py` | Manual only | Prints the Celery request |
| `downloads.tasks.upload_media_to_s3` | `backend/downloads/tasks.py` | No caller | Would upload a local file with boto3 and update `Download` |

Configuration is `CELERY_BROKER_URL` (default `redis://127.0.0.1:6379/0`) and `CELERY_RESULT_BACKEND` (default db 1). JSON serialization. Time zone `UTC`. There is no `CELERY_BEAT_SCHEDULE`.

The worker process is started with `celery -A config worker`. `backend/config/__init__.py` exports the Celery app so `-A config` works. On consumer start, `StartupReconciliationStep` calls `api.reconciliation.reconcile_startup_jobs` before the worker takes messages. That function:

- locks with a Postgres advisory lock when the database is PostgreSQL
- inspects non-terminal `AutomationJob` rows
- requeues work whose Celery message is gone
- can terminate an orphaned runner process group
- records what it did; it is also exposed as `manage.py reconcile_automation_jobs`

`execute_automation_job` is the only task that reaches automation. Its flow is documented in `docs/api/API_EXECUTION_FLOWS.md` and `docs/architecture/ORCHESTRATOR_ARCHITECTURE.md`.

Retries inside that task are narrow. Only `scrape_profile`, and only while the job is still `running`, uses `self.retry` with `max_retries=2`. Other failures mark the job `failed`. Recovery from a dead worker is a separate generation fence in `resolve_execution_recovery`, not a blanket Celery retry.

## Other background processes

| Process | How it starts | Relationship to the API |
| --- | --- | --- |
| `orchestrator.runner_process` | `subprocess.Popen` from `BrowserRunnerSupervisor` inside the Celery task | One process per running job. Authenticated Unix socket. Stopped with `SIGTERM`/`SIGKILL` on the process group when the supervisor closes |
| Daphne / ASGI | Installed app and `ASGI_APPLICATION`, but Compose runs `runserver` | WebSocket route exists. Job code does not push events |
| Spark master | Compose profile `analytics` | Idle relative to Django unless an operator submits a job from outside this repository |
| Node service | Compose profile `optional-data` | Not imported by the API |

The unused in-process runner `backend/api/local_tasks.py` was removed. Automation is queued only through Celery.

## What triggers Spark today

No API, service, orchestrator method, or Celery task triggers Spark. An operator would have to start the `analytics` profile and run a `spark_jobs` module themselves. The batch and ML functions still need a Spark session and a source dataframe or Mongo collection that this repository does not populate.

## Operational implications

- Queue trouble for automation is Redis plus the Celery worker, not Spark.
- A job stuck in `queued` means the worker is down, waiting on the Compose debugpy `--wait-for-client` flag, or the broker publish failed and the row should already be `failed`.
- A job stuck in `running` is the runner or the account lock. Check `runner_pid`, `runner_ipc_path`, `runner_heartbeat_at`, and `AccountBrowserLock.expires_at`. Detailed health reads those fields and does not repair them.
- Download-table rows and S3 settings do not move unless something outside the current callers invokes `upload_media_to_s3` or a job uses action `download`.
