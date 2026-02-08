# 🔗 Orchestrator Integration Module

> Bridges **ALL** automation modules with the backend API.

---

## Architecture

```
                       ┌───────────────────┐
                       │   BACKEND API     │
                       │   Django REST     │
                       └─────────┬─────────┘
                                 │
                       ┌─────────▼─────────┐
                       │   ORCHESTRATOR    │
                       │   unified_worker  │
                       └─────────┬─────────┘
                                 │
       ┌───────────┬─────────────┼─────────────┬───────────┐
       ▼           ▼             ▼             ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│Playwright│ │ Selenium │ │  Scrapy  │ │Downloader│ │  Safety  │
│ Adapter  │ │ Adapter  │ │ Adapter  │ │ Adapter  │ │ Adapter  │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
     │            │            │            │            │
┌─────────────────────────────────────────────────────────────────┐
│                    AUTOMATION MODULES                           │
├─────────────────────────────────────────────────────────────────┤
│ browser_manager │ driver_manager │ spiders │ media_downloader │ │
│ InstagramBrowser│ DriverManager  │ Hashtag │ MediaDownloader  │ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Basic Usage (Single Adapter)

```python
from orchestrator import UnifiedWorker, AdapterType, TaskType

async def main():
    worker = UnifiedWorker(account_id=1)
    
    # Scrape profiles with Playwright
    result = await worker.execute(
        adapter_type=AdapterType.PLAYWRIGHT,
        task_type=TaskType.SCRAPE_PROFILE,
        targets=["instagram", "cristiano"]
    )
    
    print(f"Scraped: {result.items_processed}")
    await worker.cleanup()
```

### 2. With Fallback (Playwright → Selenium)

```python
result = await worker.execute_with_fallback(
    task_type=TaskType.SCRAPE_PROFILE,
    targets=["instagram"],
    primary=AdapterType.PLAYWRIGHT,
    fallback=AdapterType.SELENIUM
)
```

### 3. With Safety Checks (Rate Limiting)

```python
result = await worker.execute_with_safety(
    adapter_type=AdapterType.PLAYWRIGHT,
    task_type=TaskType.FOLLOW_USERS,
    targets=["user1", "user2", "user3"]
)
```

---

## Adapters Reference

### Playwright Adapter
| Task | Method |
|------|--------|
| `LOGIN` | Cookie or password login |
| `SCRAPE_PROFILE` | Extract profile info |
| `LIKE_POSTS` | Like posts by URL |
| `FOLLOW_USERS` | Follow by username |
| `UNFOLLOW_USERS` | Unfollow by username |
| `VIEW_STORIES` | View user stories |
| `COMMENT` | Comment on posts |

### Selenium Adapter
| Task | Method |
|------|--------|
| `LOGIN` | Browser login |
| `SCRAPE_PROFILE` | Profile scraping |

### Scrapy Adapter
| Task | Method |
|------|--------|
| `SCRAPE_HASHTAG` | Bulk hashtag scraping |
| `SCRAPE_PROFILE` | Profile spider |
| `SCRAPE_FOLLOWERS` | Followers list |

### Downloader Adapter
| Task | Method |
|------|--------|
| `DOWNLOAD_IMAGE` | Single image |
| `DOWNLOAD_VIDEO` | Single video |
| `DOWNLOAD_CAROUSEL` | Multi-item posts |
| `BULK_DOWNLOAD` | Parallel downloads |
| `UPLOAD_S3` | S3 upload |

### Safety Adapter
| Task | Method |
|------|--------|
| `CHECK_RATE_LIMIT` | Rate limiting |
| `GET_DELAY` | Human-like delays |
| `CHECK_HEALTH` | Account health |

---

## Environment Variables

```env
INSTABOT_API_URL=http://localhost:8000/api/v1
```

---

## File Structure

```
orchestrator/
├── __init__.py           # Module exports
├── api_client.py         # Backend REST client
├── callbacks.py          # Action logging hooks
├── cookie_sync.py        # Cookie management
├── bot_worker.py         # Legacy Playwright-only worker
├── unified_worker.py     # Multi-backend worker
├── requirements.txt      # Dependencies
└── adapters/
    ├── __init__.py
    ├── base_adapter.py       # Abstract base
    ├── playwright_adapter.py # Browser automation
    ├── selenium_adapter.py   # Backup browser
    ├── scrapy_adapter.py     # Bulk scraping
    ├── downloader_adapter.py # Media downloads
    └── safety_adapter.py     # Rate limiting
```
