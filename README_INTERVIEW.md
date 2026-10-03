# InstaBot Interview README

## 1. What is this repo?
Yeh repo ek **Instagram automation and scraping platform** hai. Main idea yeh hai ki Instagram se data, media, aur engagement actions ko automate kia ja sake, saath hi safe account management aur analytics backend milen.

## 2. Core objective
- Instagram bot accounts ko manage karna
- Browser automation se Instagram pe login, profile scrape aur actions execute karna
- Media download karna (images, videos, reels, stories, carousels)
- Backend APIs se dashboard control aur reporting provide karna
- Cookies synchronization aur session reuse karna
- Future scalability ke liye Spark / AWS / Docker / Terraform infrastructure support rakhna

## 3. Main technologies
- **Python** — main backend and automation language
- **Django** + **Django REST Framework** — backend API server
- **Playwright** — browser automation and stealth Instagram interaction
- **Selenium** — secondary browser support for automation
- **Scrapy** — public scraping spiders for profile/hashtag/followers/comments
- **React + Vite** — frontend dashboard
- **Node.js + Express + Socket.io** — realtime / websocket service
- **Redis + Celery** — task queue and async job support
- **PostgreSQL / SQLite** — default DB via Django
- **MongoDB** — Node service uses Mongoose (possible analytics or realtime storage)
- **AWS S3** — optional media upload support via `boto3`
- **Docker / Docker Compose / Terraform** — deployment and infrastructure scaffolding
- **Apache Spark** — big-data analytics pipeline support in `spark_jobs/`

## 4. Main repo structure
- `automation/` — automation logic, browser engine, scraper, downloader, safety
  - `playwright_engine/` — `InstagramBrowser` class with stealth and login logic
  - `downloader/` — `MediaDownloader` for media download + resume + S3 upload
  - `scrapy_project/instagram_scraper/` — Scrapy spiders and middlewares
  - `selenium/` — Selenium support
- `backend/` — Django backend APIs and core data model apps
  - `api/` — generic dashboard + bot control APIs
  - `account/` — bot account, proxy, session models and viewsets
  - `analytics/` — action logs, daily analytics, dashboard views
  - `downloads/` — download queue, history, media files
  - `config/` — Django project settings and URL routing
- `orchestrator/` — glue between backend and automation
  - `bot_worker.py` — session lifecycle, browser startup, login, tasks
  - `api_client.py` — backend HTTP client wrapper
  - `callbacks.py` — action logging callbacks to backend
  - `cookie_sync.py` — save/load cookies for Playwright sessions
- `frontend/` — React-based dashboard UI
- `node_service/` — WebSocket / realtime services
- `spark_jobs/` — Spark job templates for batch/streaming/ML
- `infradocker/`, `infrascripts/`, `infraterraform/` — deployment and infrastructure
- `docs/` — documentation and roadmap

## 5. How data / flow works
### 5.1 User / dashboard request
1. Frontend sends request to Django API.
2. API validates request and updates bot account / session state.
3. Orchestrator or worker uses backend API to fetch account info and start a session.
4. Browser automation starts via `InstagramBrowser`.
5. Authentication is attempted with saved cookies; fallback to fresh login if needed.
6. Requested task runs:
   - scrape profile
   - download media
   - follow/like/unfollow
   - view stories
7. Actions are logged back to backend using `ActionCallback`.
8. Cookies are synced to backend using `CookieSync`.
9. Session ends and backend marks it complete.

### 5.2 Media download flow
- `MediaDownloader._download_media()` handles image/video downloads.
- It supports resume using HTTP `Range` if server allows.
- `bulk_download()` downloads multiple files in parallel.
- `download_carousel()` downloads carousel items in order.
- `upload_to_s3()` is optional if AWS credentials are available.

## 6. Why both Playwright and Scrapy?
- **Playwright** is used for logged-in automation and real Instagram interaction.
- **Scrapy** is used for faster public data crawling without opening a browser.
- Dono complementary hain: Playwright heavy work, Scrapy lightweight scraping.

## 7. Important backend APIs
### `backend/config/urls.py`
- `api/v1/` — main API prefix
- `api/v1/token/` — JWT auth
- `api/v1/docs/`, `api/v1/redoc/` — API docs
- `api/v1/bots/status/` — current bot sessions
- `api/v1/bots/control/` — start/stop/pause/resume bots
- `api/v1/rate-limits/` — account safety limits
- `api/v1/health/` — service health
- `api/v1/downloads/` — download queue and file APIs
- `api/v1/analytics/` — analytics dashboard and account stats
- `api/v1/accounts/` — bot account and proxy management

## 8. What is interview-worthy about this repo?
### Architecture understanding
- This repo demonstrates a **full-stack automation product**.
- It separates **automation**, **orchestration**, **backend**, **frontend**, and **infra**.
- It handles both **logged-in browser automation** and **public web scraping**.

### Technical depth
- Uses **Playwright** with stealth/human-like behavior.
- Includes **cookie sync** for session reuse.
- Implements **action logging** and **analytics**.
- Has a **Django REST API** with JWT and Swagger docs.
- Supports **proxy rotation**, **rate limits**, **retry logic** and **task queue** design.

### Business value
- Can manage **multiple bot accounts** safely.
- Can collect **Instagram data + media** for research/dashboard use.
- Can perform **automation actions** (scrape, download, follow, like).
- Can be extended to **cloud deployment** and **big-data analytics**.

## 9. Notes on current repo status
- Backend is functional and includes lots of API endpoints.
- Frontend exists but I did not verify full UI behavior in this read.
- Scrapy spiders are present as a separate scraping option.
- Spark and infra modules exist for scaling, but may be more roadmap than finished product.
- The project is clearly designed as a prototype / educational enterprise stack.

## 10. How to explain this in interview
Use this structure:
1. **Problem**: “We need a platform to automate Instagram scraping and actions safely.”
2. **Solution**: “This repo builds a full-stack InstaBot system with backend APIs, browser automation, media download, and analytics.”
3. **Architecture**: Explain `automation/`, `orchestrator/`, `backend/`, `frontend/`, `node_service/`, and `spark_jobs/`.
4. **Tech stack**: Python, Django, Playwright, React, Node.js, Redis, Celery, Docker, AWS.
5. **Key flows**: session start → browser login → task execution → action logging → cookie sync.
6. **Why it is robust**: cookie persistence, proxy support, safe action limits, export feature, API docs.

---

### Quick list of exact interviewer points
- `BotWorker` runs bot sessions.
- `InstagramBrowser` manages Playwright browser and login.
- `MediaDownloader` downloads images/videos/reels/stories.
- `CookieSync` saves/restores cookies to backend.
- `InstaApiClient` calls backend APIs from orchestrator.
- `ActionCallback` logs bot actions to the backend.
- Scrapy spiders exist for profile/hashtag/follower/comment scraping.
- Django backend serves API routes, JWT auth, docs, analytics, downloads.
- Node service provides realtime WebSocket capabilities.
- Spark jobs are available for big-data pipeline expansion.

> This README is written for an interviewer: it shows that you understand what the repo does, how it is organized, what technologies it uses, and how the main flows work.
