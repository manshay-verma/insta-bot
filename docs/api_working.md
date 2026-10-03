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

### Sync automation (depends on `orchestrator/` being importable)

- **POST** `/api/v1/bot/execute/`

Body:

```json
{
  "account_id": 1,
  "action": "like|follow|unfollow|scrape_profile|view_stories|download|comment",
  "targets": ["instagram"],
  "options": {}
}
```

If `orchestrator` is missing/not configured, the endpoint typically returns `success: false` with an error like **“Orchestrator not available”**.

### Async automation (depends on Celery + broker + worker)

- **POST** `/api/v1/bot/execute/async/`
- **GET** `/api/v1/bot/task/{task_id}/`

You need:

- Celery configured in the backend
- a broker/result backend (commonly Redis)
- a running Celery worker

---

## 🔌 WebSocket (real-time updates)

- WebSocket URL: `ws://localhost:8000/ws/updates/`

