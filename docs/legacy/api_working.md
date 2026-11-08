# ✅ Working API Endpoints (Backend)

Base URL (local):

- Backend: `http://localhost:8000`
- API v1: `http://localhost:8000/api/v1/`

Notes:

- **“Working”** here means the route is wired and implemented in the Django backend.
- Some endpoints **depend on extra services** (Celery/Redis) or extra code (`orchestrator/`). Those are called out explicitly.

---

## 🔎 Health + API Docs (works without Celery)

- **GET** `/api/v1/health/`
- **GET** `/api/v1/schema/`
- **GET** `/api/v1/docs/` (Swagger UI)
- **GET** `/api/v1/redoc/`

---

## 🔐 Auth (JWT) (works without Celery)

These are the real JWT endpoints in the codebase (SimpleJWT):

- **POST** `/api/v1/token/`
- **POST** `/api/v1/token/refresh/`
- **POST** `/api/v1/token/verify/`

---

## 👤 Dashboard User + Settings (works without Celery)

- **POST** `/api/v1/register/`

Body:

```json
{ "username": "u1", "email": "u1@example.com", "password": "Password123" }
```

- **GET** `/api/v1/settings/`
- **POST** `/api/v1/settings/`

Body (example):

```json
{
  "theme": "dark",
  "notifications": { "browser": true, "email": false, "webhooks": true },
  "proxy_settings": { "globalProxy": "", "trustLevel": "medium" }
}
```

---

## 🤖 Bot Status + Controls (works without Celery)

These endpoints **update DB state** (sessions/accounts) for the dashboard.

- **GET** `/api/v1/bots/status/`
- **POST** `/api/v1/bots/control/`

Body:

```json
{ "action": "start|stop|pause|resume", "account_id": 1 }
```

Important:

- `action=start` currently **creates a `Session` row**. It does **not** run real automation by itself.

- **POST** `/api/v1/bots/control/bulk/`

Body:

```json
{ "action": "start_all|stop_all|pause_all|resume_all" }
```

---

## 📡 System + Schedule + Maintenance (works without Celery)

- **GET** `/api/v1/system/status/`
- **GET** `/api/v1/schedule/upcoming/` (currently returns `{ "items": [] }`)
- **POST** `/api/v1/maintenance/cleanup/`

Body (optional):

```json
{ "cutoff_days": 30 }
```

---

## ⏱️ Rate Limits (works without Celery)

- **GET** `/api/v1/rate-limits/`
- **GET** `/api/v1/rate-limits/?account_id=1`

---

## 📤 Exports (works without Celery)

These write export files to disk (under `artifacts/exports/`) and store an `ExportJob` in the DB.

- **POST** `/api/v1/exports/`

Body:

```json
{
  "export_format": "json|csv|zip",
  "data_types": ["analytics", "actions", "downloads", "media_files", "system_status"]
}
```

- **GET** `/api/v1/exports/history/`
- **GET** `/api/v1/exports/stats/`
- **GET** `/api/v1/exports/{job_id}/download/`

---

## 🧩 Account / Proxy / Session CRUD (DRF router)

These are router-based endpoints from the `account` app:

- **GET/POST** `/api/v1/accounts/`
- **GET/PATCH/DELETE** `/api/v1/accounts/{id}/`
- **GET** `/api/v1/accounts/{id}/health/`
- **POST** `/api/v1/accounts/{id}/update_cookies/`

- **GET/POST** `/api/v1/proxies/`
- **GET/PATCH/DELETE** `/api/v1/proxies/{id}/`

- **GET/POST** `/api/v1/sessions/`
- **GET/PATCH/DELETE** `/api/v1/sessions/{id}/`

---

## 📊 Analytics APIs

### Summary endpoints

- **GET** `/api/v1/analytics/dashboard/`
- **GET** `/api/v1/analytics/accounts/{account_id}/stats/`

### Router endpoints

- **GET/POST** `/api/v1/analytics/daily/`
- **GET/POST** `/api/v1/analytics/actions/`
- **GET/POST** `/api/v1/analytics/behaviors/`

---

## 📥 Downloads APIs

Important: downloads are mounted at `/api/v1/downloads/` and the router inside uses `downloads`, so you get `/downloads/downloads/`.

- **GET/POST** `/api/v1/downloads/downloads/`
- **GET/PATCH/DELETE** `/api/v1/downloads/downloads/{id}/`
- **GET** `/api/v1/downloads/downloads/{id}/status/`
- **POST** `/api/v1/downloads/downloads/bulk/` (creates `DownloadQueue` items)

- **GET/POST** `/api/v1/downloads/queue/`
- **POST** `/api/v1/downloads/queue/{id}/process/` (creates a `Download` record)

- **GET** `/api/v1/downloads/files/`
- **GET** `/api/v1/downloads/history/`

---

## ⚡ Real Automation (depends on extra services/code)

### Automation jobs (Celery worker execution)

- **POST** `/api/v1/bot/execute/`
- **POST** `/api/v1/bot/execute/async/` (legacy alias; same asynchronous path)

Body:

```json
{
  "account_id": 1,
  "action": "like|follow|unfollow|scrape_profile|view_stories|download|comment",
  "targets": ["instagram"],
  "options": {}
}
```

Both submit routes validate ownership and persist a job before queueing it. They return `job_id`, `task_id`, and a job status; they do not execute automation in the Django request process. An optional `Idempotency-Key` header makes safe client retries return the original job.

- **GET** `/api/v1/bot/jobs/{job_id}/` — durable job status
- **POST** `/api/v1/bot/jobs/{job_id}/cancel/` — cancel queued work or request cancellation of a running job
- **GET** `/api/v1/bot/task/{task_id}/` — legacy status lookup by Celery task ID

Automation is executed only by the Celery worker, which owns the Playwright package and browser binaries. Django persists job state in PostgreSQL; Redis is the Celery broker. A running worker and reachable backend API are required. Cancellation of a running job is cooperative at job completion and does not interrupt an in-progress browser run.

---

## 🔌 WebSocket (real-time updates)

- WebSocket URL: `ws://localhost:8000/ws/updates/`
