# Component integration matrix

Status values:

- **WORKING** — a production caller invokes the callee and uses the result.
- **PARTIAL** — the call exists, but an important part of the behavior is missing or only some of the data moves.
- **BROKEN** — the code tries to perform the integration and cannot succeed as written, or the expected direction is implemented backwards and the expected call does not exist.
- **UNUSED** — the callee exists and has no production caller. An import inside an uncalled adapter does not count as working.
- **UNKNOWN** — not distinguishable from the repository alone.

| Link | Status | Evidence |
| --- | --- | --- |
| API → service, automation submit | WORKING | `BotExecuteView.post` calls `submit_automation_job` in `backend/api/job_service.py`, which inserts `AutomationJob` and calls `execute_automation_job.apply_async`. |
| API → service, dashboard and download routes | UNUSED | Those views call the ORM directly. The empty `backend/services/` package was removed. |
| Service → orchestrator | PARTIAL | `job_service` does not import the orchestrator. The Celery task it enqueues does. The link is real and asynchronous. |
| Orchestrator → automation | WORKING | `runner_process._execute_payload` constructs `UnifiedWorker`, which constructs `PlaywrightAdapter` or `DownloaderAdapter`. Those adapters call `InstagramBrowser` and `MediaDownloader`. |
| Orchestrator → Celery | UNUSED | No orchestrator module imports Celery or calls `apply_async`. The dependency runs from Celery into the orchestrator. |
| Celery → automation | WORKING | `api.execute_automation_job` starts `BrowserRunnerSupervisor`, which starts `orchestrator.runner_process`, which runs the adapter. |
| Automation → browser | WORKING | `PlaywrightAdapter` calls `InstagramBrowser` in `automation/playwright_engine/browser_manager.py` for the non-download actions. |
| Automation → database | PARTIAL | Sessions, cookies, and action logs go through `InstaApiClient` HTTP and land in Django models. Password decrypt uses the ORM inside the runner. Download jobs do not write `downloads.Download`. Selenium, Scrapy, and safety do not run. |
| Automation → Redis | PARTIAL | The OTP waiter in the runner uses the Celery broker Redis. `RedisRateLimiter` is not called by Playwright or by the job task. |
| Orchestrator → Spark | UNUSED | No import of `spark_jobs` or `pyspark` under `orchestrator/` or `backend/`. |
| Spark → storage or database | UNUSED | `spark_jobs/batch/hashtag_trending.py` and `spark_jobs/spark_app.py` would write MongoDB. `spark_jobs/ml/recommendation_als.py` would write `s3a://instabot-analytics/...`. Nothing calls those functions. `spark_app.py` also calls `SparkSession.builder.get_create()`, which is not a PySpark API, so the script would fail if invoked. |
| Background worker → result processing | WORKING | `execute_automation_job` writes `status`, `result`, `error`, and `completed_at` on `AutomationJob` after the runner returns, and drops stale generations. |
| Result processing → API or database | PARTIAL | Results are stored on `AutomationJob` and returned by `GET /api/v1/bot/jobs/{id}/`. Action rows are written during the run, not by the final result writer. No code publishes the result to `ws/updates/`. |
| Celery → S3 upload task | UNUSED | `downloads.tasks.upload_media_to_s3` is never called. |
| Download API → media downloader | UNUSED | Queue and download views only insert rows. The downloader runs from job action `download`, which ignores those rows. |
| WebSocket consumer → job updates | UNUSED | `BotUpdatesConsumer` is mounted. No `group_send` to `bot_updates` exists. |
| Bot control `start` → browser | BROKEN | The route is named and documented in older notes as starting a bot. The view only creates a `Session` row. The browser starts later, and only from a queued automation job. |
| Safety module → live actions | UNUSED | `SafetyAdapter` and `automation/safety` have no caller on the execute map. |
| Selenium and Scrapy adapters → live actions | UNUSED | `UnifiedWorker._create_adapter` can build them. `execute_automation_job` never requests them. |
| `api.healthcheck` → lock reconciliation | PARTIAL | The task calls `reconcile_expired_locks`, but no Beat schedule or HTTP route enqueues it. Startup reconciliation is a different function and does run when the worker consumer starts. |
| Worker token → Django | WORKING | `InstaApiClient` sends `X-Worker-Token`. `WorkerTokenAuthentication` allows the account, cookie, session, bot-control, action-log, and health paths that the client uses. |

## Caller notes that are easy to misread

- `backend/api/tasks.py` imports `UnifiedWorker` and does not reference it. The live construction site is `orchestrator/runner_process.py`.
- `orchestrator/__init__.py` re-exports every adapter. Export lists are not callers.
- Compose mounts `./spark_jobs` into the optional `spark-master` service. Mounting the directory does not submit a job.
- `GET /api/v1/health/detailed/` inspects Celery and runner processes. Inspection is not execution.
