## Local development flow (Frontend ↔ Backend ↔ Automation)

This document explains how the **React frontend**, **Django backend**, and **automation worker** connect and how requests flow in local development.

### Components you run locally

- **Frontend (Vite + React)**: runs on `http://localhost:5173`
- **Backend (Django + DRF + Channels)**: runs on `http://localhost:8000`
- **Postgres**: used by backend when `DB_*` env vars are set (Docker)
- **Redis**: used as the Celery broker/result backend (and can be used for Channels if you later switch)
- **Automation (Celery worker container)**: executes long-running bot tasks

Spark and the Node websocket service are **optional** and not required for the core local dev flow.

---

### High-level flow diagram

```text
Browser (React @5173)
  |
  |  REST calls (axios) to VITE_API_URL
  v
Django API (DRF @8000)
  |
  |  (A) Sync: runs orchestrator immediately in-process
  |  (B) Async: pushes a job to Celery via Redis
  v
Automation execution (Celery worker / orchestrator)
  |
  |  writes results/logs
  v
Postgres (state, logs, accounts, analytics)

Real-time updates:
React <--- WebSocket --- Django Channels  ws://localhost:8000/ws/updates/
```

---

### Frontend → Backend (REST)

The frontend uses Axios with:

- **Base URL**: `import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"`
- **JWT**: attaches `Authorization: Bearer <token>` when `localStorage.token` exists

See `frontend/src/services/api.js`.

Useful backend endpoints (local):

- **API docs**: `http://localhost:8000/api/v1/docs/`
- **JWT token**: `POST /api/v1/token/`
- **Health check**: `GET /api/v1/health/`
- **Execute bot (sync)**: `POST /api/v1/bot/execute/`
- **Execute bot (async)**: `POST /api/v1/bot/execute/async/`
- **Task status (async)**: `GET /api/v1/bot/task/<task_id>/`

Routing is in `backend/config/urls.py` and `backend/api/urls.py`.

---

### Backend → Automation (two modes)

#### Mode A: Sync execution (simple dev)

When you call:

- `POST /api/v1/bot/execute/`

The backend imports the orchestrator and executes immediately inside the Django process:

- `backend/api/bot_execute.py` calls `asyncio.run(...)`
- It uses `orchestrator.UnifiedWorker` to start a session, execute the task, and clean up

This is easiest for quick testing, but it ties up the API request while the action runs.

#### Mode B: Async execution (recommended for long jobs)

When you call:

- `POST /api/v1/bot/execute/async/`

The backend enqueues a Celery job:

- Celery broker: `CELERY_BROKER_URL` (Redis)
- Worker container consumes the job and runs the automation
- You get back a `task_id`, then poll:
  - `GET /api/v1/bot/task/<task_id>/`

This is better for long-running browser automation.

---

### Backend ↔ Database (Postgres vs SQLite)

`backend/config/settings.py` is set up like this:

- If `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` are set, Django uses **Postgres**
- Otherwise it falls back to **SQLite** (`backend/db.sqlite3`)

In Docker Compose, the backend receives `DB_*` variables, so it will use Postgres.

---

### Real-time updates (WebSockets)

The backend exposes a websocket route:

- `ws://localhost:8000/ws/updates/`

Implementation:

- `backend/api/routing.py` defines the route
- `backend/api/consumers.py` (`BotUpdatesConsumer`) joins the `"bot_updates"` group
- `backend/config/asgi.py` wires HTTP + websocket handling

In local dev, Channels is configured with:

- `channels.layers.InMemoryChannelLayer`

That’s fine for a single-process dev setup. For multi-process/production you’d usually switch to Redis channel layers.

---

### Local “connected” run checklist

- **Backend reachable**: `http://localhost:8000/api/v1/health/`
- **Frontend reachable**: `http://localhost:5173`
- **Frontend can call API**: browser network shows requests to `/api/v1/...`
- **Async automation works**:
  - API returns `task_id`
  - Worker logs show task execution
  - Task status endpoint returns `SUCCESS`/`FAILURE`

