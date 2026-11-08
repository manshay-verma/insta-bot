# Implementation Plan: Safety, Scrapy & Selenium Modules

## Overview
Implementing 26 tasks from the automation roadmap with a **modular, easy-to-debug file structure**. Each feature is in its own focused file for ease of maintenance.

---

## 🛡️ Safety Module (12 Tasks)

### Current State
- ✅ Rate limiter base class exists (`rate_limiter/base.py`)
- ✅ Memory rate limiter exists (`rate_limiter/memory_limiter.py`)
- ✅ Config exists (`config.py`)

### Proposed File Structure
```
automation/safety/
├── __init__.py                    # [MODIFY] Add new exports
├── config.py                      # [EXISTS] Already complete
├── rate_limiter/
│   ├── __init__.py               # [MODIFY] Add Redis limiter
│   ├── base.py                   # [EXISTS] Already complete
│   ├── memory_limiter.py         # [EXISTS] Already complete
│   └── redis_limiter.py          # [NEW] Task 3: Redis-backed counters
├── behavior/                      # [NEW] Human behavior simulation
│   ├── __init__.py
│   ├── delay_generator.py        # Task 5: Random delays (15-45 sec)
│   ├── sleep_schedule.py         # Task 6: Sleep hours (11 PM - 7 AM)
│   ├── action_sequencer.py       # Task 7: Randomized action sequences
│   └── warmup_manager.py         # Task 8: Warmup protocol
├── risk/                          # [NEW] Risk management
│   ├── __init__.py
│   ├── health_tracker.py         # Task 9: Account health score
│   ├── signal_detector.py        # Task 10: Detect warning/ban signals
│   └── auto_pause.py             # Task 11: Auto-pause on detection
├── logging/                       # [NEW] Action logging
│   ├── __init__.py
│   └── action_logger.py          # Task 12: Action logging for audit
└── tests/
    ├── __init__.py               # [EXISTS]
    ├── test_rate_limiter.py      # [EXISTS]
    ├── test_behavior.py          # [NEW] Tests for behavior module
    ├── test_risk.py              # [NEW] Tests for risk module
    └── test_logging.py           # [NEW] Tests for logging
```

---

## 🕷️ Scrapy Project (8 Tasks)

### Proposed File Structure
```
automation/scrapy_project/
├── scrapy.cfg                     # [NEW] Scrapy config
├── instagram_scraper/
│   ├── __init__.py
│   ├── settings.py               # [NEW] Scrapy settings
│   ├── items.py                  # [NEW] Data models
│   ├── spiders/
│   │   ├── __init__.py
│   │   ├── base_spider.py        # [NEW] Common spider logic
│   │   ├── hashtag_spider.py     # Task 1: Hashtag spider
│   │   ├── profile_spider.py     # Task 2: Profile spider
│   │   ├── comments_spider.py    # Task 3: Comments spider
│   │   └── followers_spider.py   # Task 4: Followers spider
│   ├── pipelines/
│   │   ├── __init__.py
│   │   └── mongo_pipeline.py     # Task 5: MongoDB pipeline
│   └── middlewares/
│       ├── __init__.py
│       ├── proxy_rotation.py     # Task 6: Proxy rotation
│       ├── throttle.py           # Task 7: Request throttling
│       └── retry_handler.py      # Task 8: Error handling
└── README.md                      # [NEW] Usage documentation
```

---

## 🌐 Selenium Backup (6 Tasks)

### Proposed File Structure
```
automation/selenium/
├── __init__.py                    # [NEW] Package init
├── driver_manager.py             # Task 1: Browser driver setup
├── stealth_config.py             # Task 2: Anti-detection config
├── auth/
│   ├── __init__.py
│   └── login.py                  # Task 3: Login flow
├── navigation.py                 # Task 4: Basic navigation
├── scraper/
│   ├── __init__.py
│   └── profile_scraper.py        # Task 5: Profile scraping
├── fallback_handler.py           # Task 6: Fallback from Playwright
└── tests/
    ├── __init__.py
    └── test_selenium.py          # [NEW] Basic tests
```

---

## Dependencies to Add
```
# requirements.txt additions
redis>=4.0.0           # For Redis rate limiter
scrapy>=2.11.0         # For Scrapy spiders
pymongo>=4.0.0         # For MongoDB pipeline
selenium>=4.15.0       # For Selenium backup
undetected-chromedriver>=3.5.0  # For stealth
webdriver-manager>=4.0.0        # For driver management
```
