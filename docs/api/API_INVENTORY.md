# API inventory

All HTTP routes are mounted from `backend/config/urls.py`. DRF `DefaultRouter` trailing slashes are included. Unless a row says otherwise, authentication is JWT (`Authorization: Bearer`) or HTTP Basic, and permission is `IsAuthenticated`. Worker token (`X-Worker-Token`) is accepted only on the paths listed in `backend/core/auth/worker.py`.

Unmounted code that looks like an API but is not reachable:

- `downloads.tasks.upload_media_to_s3` is a Celery task with no caller. The task module stays because the `downloads` app is installed and Celery autodiscovers it.

## Platform and auth

| Method | URL | View | Serializer | Auth | What it does | Class |
| --- | --- | --- | --- | --- | --- | --- |
| * | `/admin/` | Django admin | — | Session staff | Model admin | db-only |
| GET | `/api/v1/schema/` | `SpectacularAPIView` | OpenAPI | Default authenticated | Schema document | db-only |
| GET | `/api/v1/docs/` | `SpectacularSwaggerView` | — | Default authenticated | Swagger UI | db-only |
| GET | `/api/v1/redoc/` | `SpectacularRedocView` | — | Default authenticated | ReDoc | db-only |
| POST | `/api/v1/token/` | `TokenObtainPairView` | SimpleJWT | Allow any (view default) | Issue access and refresh tokens | db-only |
| POST | `/api/v1/token/refresh/` | `TokenRefreshView` | SimpleJWT | Allow any | Rotate refresh token | db-only |
| POST | `/api/v1/token/verify/` | `TokenVerifyView` | SimpleJWT | Allow any | Check a token | db-only |
| POST | `/api/v1/register/` | `api.views.RegisterView` | `RegisterSerializer` | `AllowAny` | Create a Django user | db-only |

`RegisterView` reads `username`, `email`, and `password` (minimum 8). It rejects duplicate username or email with `400` and returns `{id, username, email}` with `201`.

## Dashboard and operations (`backend/api/urls.py`)

| Method | URL | View | Input | Models | Downstream | Class |
| --- | --- | --- | --- | --- | --- | --- |
| GET, POST | `/api/v1/settings/` | `SettingsView` | `theme`, `notifications`, `proxy_settings` | `AppSetting` | None | db-only |
| GET | `/api/v1/bots/status/` | `BotStatusView` | — | `BotAccount`, `Session` | None | db-only |
| POST | `/api/v1/bots/control/` | `BotControlView` | `action`, `account_id` | `BotAccount`, `Session` | None. Worker token allowed | db-only |
| POST | `/api/v1/bots/control/bulk/` | `BotControlBulkView` | `action`: `start_all`, `stop_all`, `pause_all`, `resume_all` | `BotAccount`, `Session` | None | db-only |
| GET | `/api/v1/health/` | `HealthCheckView` | — | Database connectivity only | Redis `PING` on the broker URL. `AllowAny`. Worker token allowed | multi-component |
| GET | `/api/v1/health/detailed/` | `DetailedHealthCheckView` | — | Jobs and locks via `api.health` | Redis, Celery inspect, runner process identity. `AllowAny`. Does not recover jobs | multi-component |
| GET | `/api/v1/rate-limits/` | `RateLimitStatusView` | query `account_id` optional | `BotAccount`, `ActionLog` | None. Limits are constants in the view | db-only |
| GET | `/api/v1/system/status/` | `SystemStatusView` | — | `Session` | Process id and uptime only | db-only |
| GET | `/api/v1/schedule/upcoming/` | `UpcomingScheduleView` | — | None | Always `{items: []}` | disconnected |
| POST | `/api/v1/maintenance/cleanup/` | `MaintenanceCleanupView` | `cutoff_days` default 30 | `Session` | Deletes old completed, failed, or terminated sessions | db-only |
| POST | `/api/v1/exports/` | `ExportCreateView` | `ExportCreateSerializer` | `ExportJob` plus analytics/account rows it serializes | Writes a file under the exports directory in the request | db-only |
| GET | `/api/v1/exports/history/` | `ExportHistoryView` | — | `ExportJob` | None | db-only |
| GET | `/api/v1/exports/stats/` | `ExportStatsView` | — | `ExportJob` | None | db-only |
| GET | `/api/v1/exports/<job_id>/download/` | `ExportDownloadView` | path `job_id` | `ExportJob` | `FileResponse` from `file_path` | db-only |

`BotControlView` actions are `start` (insert an active `Session` if the account is `active`), `stop` (complete active sessions), `pause`, and `resume`. Unknown actions return `400`. Missing accounts return `404`. Staff see every account. Other users see accounts they own. A worker-token caller is not filtered by owner, because the view treats `request.auth == "worker"` like a cross-account operator for this one route.

## Automation jobs (`backend/api/bot_execute.py`)

| Method | URL | View | Serializer | Models | Downstream | Class |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/api/v1/bot/execute/` | `BotExecuteView` | `AutomationJobCreateSerializer` | `BotAccount`, `AutomationJob` | `submit_automation_job` → Celery `api.execute_automation_job` | background-job |
| POST | `/api/v1/bot/execute/async/` | `BotExecuteAsyncView` | same | same | same implementation as execute | background-job |
| GET | `/api/v1/bot/task/<task_id>/` | `TaskStatusView` | `AutomationJobStatusSerializer` | `AutomationJob` | Lookup by `celery_task_id` and `user`. May expire a stale OTP wait | db-only |
| GET | `/api/v1/bot/jobs/<uuid:job_id>/` | `TaskStatusView` | same | same | Lookup by job id and `user` | db-only |
| POST | `/api/v1/bot/jobs/<uuid:job_id>/verification/` | `VerificationCodeSubmitView` | `VerificationCodeSubmitSerializer` | `AutomationJob` | Redis `SET NX` on the broker URL | multi-component |
| POST | `/api/v1/bot/jobs/<uuid:job_id>/cancel/` | `JobCancelView` | none | `AutomationJob` | Celery `revoke` only when the job was `queued` or `retrying` | background-job |

Create body:

- `account_id` (integer, required)
- `action`: `like`, `follow`, `unfollow`, `scrape_profile`, `view_stories`, `download`, `comment`
- `targets`: non-empty list of strings. `follow` and `unfollow` are normalized by `normalize_instagram_profile_target`
- `options`: object. Keys that look like passwords, cookies, tokens, or secrets are rejected. `verification_callback` is rejected because the runner installs that callback itself
- header `Idempotency-Key` optional, max 128 characters

Responses:

- `202` with `{job_id, task_id, status, message}` when a new job is queued
- `200` with the same shape when the idempotency key matches an existing identical job
- `409` when the key was reused for a different payload, or another job is already active for the account
- `503` when `apply_async` raises. The job row is then marked `failed`
- `404` when the account is not visible to the user
- `400` when the account is not `active` or the body is invalid

Status payload fields: `job_id`, `task_id`, `account`, `action`, `status`, `attempt_count`, `execution_generation`, `result`, `error`, `cancel_requested`, `verification_expires_at`, `created_at`, `started_at`, `completed_at`.

Verification body: `code` (4–10 digits) and integer `execution_generation` (booleans and numeric strings are rejected). Success is `202 {"status": "received"}`. Stale generation, expired challenge, wrong status, or a code already stored returns `409`. Redis failure returns `503`.

Cancel returns the status serializer. Queued and retrying jobs become `cancelled` and the Celery task id is revoked without `terminate=True`. Running and OTP jobs become `cancelling` with `cancel_requested=True`. Terminal jobs are returned unchanged. Revoke publish failures are logged and do not fail the HTTP call.

These routes do not call Spark, the orchestrator, or Playwright inside the request process.

## Accounts (`backend/account/urls.py`)

`ProxyViewSet` (`IsAdminUser`): `/api/v1/proxies/` and `/api/v1/proxies/{id}/` with list, create, retrieve, update, partial update, and delete. Model `Proxy`. No automation.

`BotAccountViewSet`:

| Method | URL | Behavior | Class |
| --- | --- | --- | --- |
| GET, POST | `/api/v1/accounts/` | List or create. Create sets `owner` to the current user. Query `status` filters the list | db-only |
| GET, PUT, PATCH, DELETE | `/api/v1/accounts/{id}/` | Retrieve or update an owned account. Worker token may `GET` | db-only |
| GET | `/api/v1/accounts/{id}/health/` | Counts today's sessions and session action totals. Healthy means `active`, trust score ≥ 0.3, and fewer than 10 sessions today | db-only |
| POST | `/api/v1/accounts/{id}/update_cookies/` | Writes encrypted cookies and session metadata. Worker token allowed | db-only |
| POST | `/api/v1/accounts/{id}/session_status/` | Updates `session_status`. Worker token allowed | db-only |

Serializers live in `backend/account/serializers.py` (`BotAccountSerializer`, create/update variants, `AccountHealthSerializer`, cookie and session-status serializers). Password values are encrypted in `account.utils` before storage. The viewset does not start a browser.

`SessionViewSet`:

| Method | URL | Behavior | Class |
| --- | --- | --- | --- |
| GET, POST | `/api/v1/sessions/` | List or create sessions for owned accounts | db-only |
| GET, PUT, PATCH, DELETE | `/api/v1/sessions/{id}/` | Standard row operations | db-only |
| POST | `/api/v1/sessions/{id}/end/` | Sets `ended_at` and a terminal status. Worker token allowed | db-only |

The orchestrator calls `start` through `/api/v1/bots/control/` and `end` through this action. Those calls still only change rows.

## Analytics (`backend/analytics/urls.py`)

Prefix: `/api/v1/analytics/`.

| Method | URL | View | Models | Notes | Class |
| --- | --- | --- | --- | --- | --- |
| * | `/daily/` and `/daily/{id}/` | `DailyAnalyticsViewSet` | `DailyAnalytics` | Owned-account queryset | db-only |
| * | `/actions/` and `/actions/{id}/` | `ActionLogViewSet` | `ActionLog` | Worker token may `POST` | db-only |
| * | `/behaviors/` and `/behaviors/{id}/` | `UserBehaviorViewSet` | `UserBehavior` | Owned-account queryset | db-only |
| GET | `/dashboard/` | `DashboardView` | analytics aggregates | Read model for the current user's accounts | db-only |
| GET | `/accounts/{account_id}/stats/` | `AccountStatsView` | analytics for one account | `404` or permission failure when the account is not visible | db-only |

The Playwright callback posts action logs here through `InstaApiClient.log_action`. Nothing in these views starts automation or Spark.

## Downloads (`backend/downloads/urls.py`)

The include prefix is already `/api/v1/downloads/`, and the router registers `downloads`, `queue`, and `files`. The collection URLs are therefore doubled.

| Method | URL | View | Effect | Class |
| --- | --- | --- | --- | --- |
| * | `/api/v1/downloads/downloads/` and `/{id}/` | `DownloadViewSet` | CRUD on `Download`. Create requires an owned `BotAccount` | db-only |
| GET | `/api/v1/downloads/downloads/{id}/status/` | `status` action | Returns a placeholder progress value (0, 50, or 100) | db-only |
| POST | `/api/v1/downloads/downloads/bulk/` | `bulk` action | Inserts `DownloadQueue` rows. Does not start a downloader | db-only |
| * | `/api/v1/downloads/queue/` and `/{id}/` | `DownloadQueueViewSet` | CRUD on `DownloadQueue` | db-only |
| POST | `/api/v1/downloads/queue/{id}/process/` | `process` action | Creates a `pending` `Download` and marks the queue row processed. Does not fetch bytes | disconnected |
| GET | `/api/v1/downloads/files/` and `/{id}/` | `MediaFileViewSet` | Read-only `MediaFile` rows | db-only |
| GET | `/api/v1/downloads/history/` | `DownloadHistoryView` | Filters downloads by date and limit | db-only |

Media bytes are fetched only when an automation job uses `action: "download"`. That path does not read or update these download tables.

## WebSocket

| URL | Consumer | Auth | Behavior | Class |
| --- | --- | --- | --- | --- |
| `ws/updates/` | `api.consumers.BotUpdatesConsumer` | Channels `AuthMiddlewareStack` (session, not JWT) | Joins group `bot_updates` and forwards `bot_update` events | disconnected |

`backend/config/asgi.py` mounts the route. `CHANNEL_LAYERS` is `InMemoryChannelLayer`. No producer in the repository sends to `bot_updates`, so a connected client does not receive job progress.

## Error shape

Handled DRF exceptions go through `core.exceptions.api_exception_handler`, which keeps the DRF response and adds toast-oriented fields. Unhandled exceptions return `500` with `error`, `message`, `toast_type`, and `details`. Views that catch domain errors (`IdempotencyConflict`, missing accounts, Redis failures) return their own status codes before that handler runs.
