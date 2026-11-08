---
trigger: always_on
---

# Automation execution rules

Use this when editing jobs, the worker, or the runner.

1. `POST /api/v1/bot/execute/` and `POST /api/v1/bot/execute/async/` both call `BotExecuteView.post`. They return after `apply_async`. They do not open a browser.
2. Supported actions are `like`, `follow`, `unfollow`, `scrape_profile`, `view_stories`, `download`, and `comment` (`AutomationJobCreateSerializer`).
3. Only `download` uses `DownloaderAdapter`. The other six use `PlaywrightAdapter`.
4. One active job per account is a database constraint. A second insert raises `AccountJobAlreadyActive` and the API returns 409.
5. Do not put passwords, cookies, tokens, or `verification_callback` in job `options`. The runner installs the OTP callback itself.
6. Result writes must keep the `execution_generation` filter. A stale runner must not overwrite a newer attempt.
7. Account browser ownership is `AccountBrowserLock`, not `Session`. `POST /api/v1/bots/control/` with `start` only inserts a session row.
8. The runner is `python -m orchestrator.runner_process`, started by `BrowserRunnerSupervisor`, with socket authentication. Do not call Playwright inside the Django request process.
9. OTP delivery is Redis `SET NX` on `CELERY_BROKER_URL`, key from `otp_redis_key(job_id, execution_generation)`.
10. Cancel of a queued job revokes the Celery message with `terminate=False`. Cancel of a running job sets `cancel_requested` and status `cancelling`. It does not by itself kill the runner.
11. Celery retries in `execute_automation_job` apply only to `scrape_profile` while status is `running`, max two retries.
12. `INSTABOT_FAKE_BROWSER=1` makes the runner skip Instagram. Do not enable it on a normal worker.

Compose worker command uses `--pool=solo` and debugpy `--wait-for-client`. A worker that never consumes may be waiting for a debugger.

Worker HTTP callbacks use `X-Worker-Token` and only the paths in `WorkerTokenAuthentication.allowed_paths`.
