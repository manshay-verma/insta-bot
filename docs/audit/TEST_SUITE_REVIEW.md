# Test suite review

Counts are `def test_` methods in the files that remain after cleanup.

| File | Methods | Class |
| --- | --- | --- |
| `backend/api/test_account_locks.py` | 23 | Active regression. Locks, fencing, recovery. |
| `backend/api/test_observability.py` | 57 | Active regression. Health and log redaction. |
| `backend/api/test_automation_jobs.py` | 17 | Active regression. Execute, status, OTP, cancel. |
| `backend/api/test_instagram_targets.py` | 18 | Active regression. Target normalization and follow result shape. |
| `backend/api/test_browser_runner.py` | 11 | Active regression. IPC auth and runner identity. |
| `backend/api/test_startup_reconciliation.py` | 11 | Active regression. Startup reconciliation. |
| `backend/account/test_session_management.py` | 12 | Active regression. Cookies and session status. |
| `automation/playwright_engine/tests/test_2fa_verification.py` | 18 | Active for browser login challenges. |
| `automation/playwright_engine/tests/test_cookie_persistence.py` | 8 | Active. Imports `BotWorker`. |
| `automation/playwright_engine/tests/test_profile_persistence.py` | 4 | Active for the persistent profile. |
| `backend/api/test_automation_task_results.py` | 4 | Active. Task result handling. |
| `automation/safety/tests/test_rate_limiter.py` | 15 | Active for the safety package, which is not on the job path. |
| `automation/downloader/test_downloader.py` | 3 | Active unit tests for `MediaDownloader`. |
| **Total retained** | **201** | |

No historical test-report file was found in the repository. A previous pass result was not used as a reason to delete anything.

## Removed

| What | Reason |
| --- | --- |
| `test/playwright/*.py` (15 scripts) | Manual demos, not Django tests. They import `browser_manager` as a top-level module, open a headed browser, and several files hardcode an account password. They do not cover Celery, locks, or the runner. |
| `backend/account/tests.py`, `backend/analytics/tests.py`, `backend/downloads/tests.py` | Django placeholders with zero test methods. Coverage for accounts lives in `test_session_management.py`. |

Nothing in the retained set was deleted. There were no duplicate methods that asserted the same behavior as a better test.

## Executed in this cleanup

| Command | Result |
| --- | --- |
| Backend container: `manage.py test api.test_automation_jobs api.test_account_locks` | 40 tests, OK. The same process also tried to load `api.test_instagram_targets` and `api.test_startup_reconciliation` and failed at import because that container's mount does not include `automation/` or `orchestrator/`. |
| Worker image: `manage.py test api.test_instagram_targets api.test_startup_reconciliation api.test_automation_task_results` | 32 tests, OK. |

## Not executed

- `test_observability.py` (57)
- `test_browser_runner.py` (11)
- `account/test_session_management.py` (12)
- `automation/playwright_engine/tests/` (30)
- `automation/safety/tests/test_rate_limiter.py` (15)
- `automation/downloader/test_downloader.py` (3)
- `backend/api/d16_failure_harness.py` (manual scenarios, not a `TestCase`)

## Missing coverage that is still worth adding

- `DownloaderAdapter` through `execute_automation_job` for action `download`, including the fact that it does not write `downloads.Download`.
- A test that Celery autodiscovery imports `downloads.tasks` without requiring `boto3` until the task body runs.
- An API test that `POST /api/v1/bots/control/` `start` creates a `Session` and does not enqueue `api.execute_automation_job`.
- No test publishes or expects a WebSocket `bot_update`. That matches the code, and it should stay that way until a producer exists.
