# 🤖 InstaBot API Guide

Simple and easy-to-understand guide for all backend APIs.

---

## � How to use these APIs?

1.  **Interact via UI**: Open [http://127.0.0.1:8000/api/v1/docs/](http://127.0.0.1:8000/api/v1/docs/) for an interactive dashboard.
2.  **Base URL**: `http://127.0.0.1:8000/api/v1/`
3.  **Format**: All data is sent and received in **JSON** format.

---

## 1. � Managing Bot Accounts & Proxies
Store and monitor your Instagram accounts and the proxies they use.

| API Endpoint | What it does? | How it works? |
| :--- | :--- | :--- |
| `POST /accounts/` | **Add a Bot** | Register a new Instagram account. |
| `GET /accounts/` | **List Bots** | See all your bots and their trust scores. |
| `GET /accounts/{id}/health/` | **Bot Health** | Checks if a bot is banned or safe to use. |
| `POST /accounts/{id}/update_cookies/` | **Update Cookies** | Save login session from Playwright to avoid re-login. |
| `POST /proxies/` | **Add Proxy** | Register a host:port for your bots to use. |

---

## 2. 🤖 Bot Control & Safety
Commands to start/stop the bots and track their safe limits.

| API Endpoint | What it does? | How it works? |
| :--- | :--- | :--- |
| `POST /bots/control/` | **Start/Stop Bot** | Send `{"action": "start", "account_id": 1}` to begin a session. |
| `GET /bots/status/` | **Who's Working?** | Shows which accounts are currently running right now. |
| `GET /rate-limits/` | **Safety Check** | Shows how many likes/follows are left before hitting limits. |
| `GET /health/` | **Server Status** | Quick check if the Backend is online. |

---

## 3. 📥 Media Downloads
Manage photos, videos, and carousels you want to save.

| API Endpoint | What it does? | How it works? |
| :--- | :--- | :--- |
| `POST /downloads/bulk/` | **Queue URLs** | Add a list of Instagram URLs to the download queue. |
| `GET /queue/` | **Pending Tasks** | See what is waiting to be downloaded. |
| `POST /queue/{id}/process/` | **Run Task** | Manually trigger a specific download task. |
| `GET /downloads/{id}/status/` | **Progress** | % progress of a specific file being downloaded. |
| `GET /history/` | **Previous Work** | List of everything you have ever downloaded. |

---

## 📊 4. Analytics & Tracking
Understand how your bots are performing over time.

| API Endpoint | What it does? | How it works? |
| :--- | :--- | :--- |
| `GET /analytics/dashboard/` | **Snapshot** | Total follows, likes, and active bots for today. |
| `GET /analytics/actions/` | **Action History** | A log of every single click and follow made by bots. |
| `GET /analytics/accounts/{id}/stats/` | **Per-Bot Stats** | Performance details for one specific account. |

---

## 🛠️ Common Workflows (Plain English)

### How to start a scraping task?
1.  **Register a bot**: `POST /accounts/`
2.  **Add a proxy**: `POST /proxies/` (optional but recommended)
3.  **Start session**: `POST /bots/control/` with `action: "start"`
4.  **Monitor progress**: `GET /bots/status/`

### How to download 50 Reels?
1.  **Add to queue**: `POST /downloads/bulk/` with an array of 50 URLs.
2.  **Wait for processing**: The bot will pick these up automatically.
3.  **Check status**: `GET /history/` to see files saved to S3.

---

## 🏗️ Missing APIs (Work in Progress)

The following features are planned for future updates:

1.  **Targeted Scraping**: `POST /tasks/scrape/` (Target specific @usernames or #hashtags).
2.  **User Authentication**: JWT login for humans to access this dashboard.
3.  **S3 Config**: Endpoints to manage your AWS/Storage settings.
4.  **CSV Export**: Export analytics and history to Excel/CSV.
5.  **Webhook Notifications**: Auto-ping your app when a download is finished.
