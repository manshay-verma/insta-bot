<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Django-4.2-green?style=for-the-badge&logo=django&logoColor=white" alt="Django"/>
  <img src="https://img.shields.io/badge/Playwright-1.40-orange?style=for-the-badge&logo=playwright&logoColor=white" alt="Playwright"/>
  <img src="https://img.shields.io/badge/AWS-Cloud-yellow?style=for-the-badge&logo=amazonaws&logoColor=white" alt="AWS"/>
  <img src="https://img.shields.io/badge/Spark-Big%20Data-red?style=for-the-badge&logo=apachespark&logoColor=white" alt="Spark"/>
</p>

<h1 align="center">🤖 Instagram Exploration & Automation Bot</h1>
<h3 align="center">Educational Project for Learning Enterprise-Grade Development</h3>

<p align="center">
  <strong>⚠️ STRICTLY FOR EDUCATIONAL PURPOSES ONLY ⚠️</strong><br>
  Use only with your own dummy accounts in your own environment.
</p>

---

# 📖 Table of Contents

1. [Project Overview](#-project-overview)
2. [Why This Project?](#-why-this-project-motivation)
3. [Core Features](#-core-features)
4. [System Architecture](#-system-architecture)
5. [Complete Workflow](#-complete-workflow)
6. [Technology Stack](#-technology-stack-detailed)
7. [Module Documentation](#-module-documentation)
8. [Data Flow](#-data-flow)
9. [API Reference](#-api-reference)
10. [Database Schema](#-database-schema)
11. [Safety & Rate Limiting](#-safety--rate-limiting)
12. [AWS Infrastructure](#-aws-infrastructure)
13. [Installation Guide](#-installation-guide)
14. [Usage Examples](#-usage-examples)
15. [Project Structure](#-project-structure)
16. [Contributing](#-contributing)
17. [License & Disclaimer](#-license--disclaimer)

---

# 🎯 Project Overview

## What Is This?

This is a **full-stack educational project** that simulates an enterprise-grade Instagram exploration and automation system. It teaches you how to build:

- **Browser automation** that mimics human behavior
- **Web scraping** at scale with multiple tools
- **Backend APIs** with Django & Node.js
- **Big Data pipelines** with Apache Spark
- **Machine Learning** for recommendations
- **Cloud deployment** on AWS
- **Real-time dashboards** with React

## The Big Picture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        INSTAGRAM EXPLORATION BOT                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   USER                                                                        │
│     │                                                                         │
│     ▼                                                                         │
│   ┌─────────────────┐                                                         │
│   │ React Dashboard │ ◄──── View stats, control bots, download media         │
│   └────────┬────────┘                                                         │
│            │                                                                  │
│            ▼                                                                  │
│   ┌─────────────────┐        ┌─────────────────┐                             │
│   │   Django API    │◄──────►│   Node.js WS    │ ◄── Real-time updates       │
│   └────────┬────────┘        └─────────────────┘                             │
│            │                                                                  │
│            ▼                                                                  │
│   ┌─────────────────┐                                                         │
│   │  Bot Controller │ ◄──── Rate limits, scheduling, safety                  │
│   └────────┬────────┘                                                         │
│            │                                                                  │
│            ▼                                                                  │
│   ┌─────────────────┐        ┌─────────────────┐                             │
│   │   Playwright    │───────►│   Instagram     │ ◄── Scrape & automate       │
│   │   (Browser)     │◄───────│   (Target)      │                             │
│   └────────┬────────┘        └─────────────────┘                             │
│            │                                                                  │
│            ▼                                                                  │
│   ┌─────────────────────────────────────────────┐                            │
│   │            DATA STORAGE LAYER               │                            │
│   │  PostgreSQL │ MongoDB │ Redis │ AWS S3      │                            │
│   └────────┬────────────────────────────────────┘                            │
│            │                                                                  │
│            ▼                                                                  │
│   ┌─────────────────┐        ┌─────────────────┐                             │
│   │ Apache Spark    │───────►│ ML Engine       │ ◄── Recommendations         │
│   │ (ETL Pipeline)  │        │ (ALS Algorithm) │                             │
│   └─────────────────┘        └─────────────────┘                             │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

# 🧠 Why This Project? (Motivation)

## Learning Goals

| # | Skill Area | What You Learn |
|---|------------|----------------|
| 1 | **Web Scraping** | Multiple tools (Requests, BS4, Scrapy, Selenium, Playwright) |
| 2 | **Browser Automation** | Human-like behavior, anti-detection, session management |
| 3 | **Backend Development** | Django REST APIs, authentication, database design |
| 4 | **Database Engineering** | PostgreSQL (SQL) + MongoDB (NoSQL) + Redis (Cache) |
| 5 | **Cloud Computing** | AWS services (EC2, RDS, S3, Lambda, Glue) |
| 6 | **Big Data** | Apache Spark, PySpark, ETL pipelines |
| 7 | **Machine Learning** | Collaborative filtering, recommendations |
| 8 | **Real-time Systems** | WebSockets, Node.js, live updates |
| 9 | **Frontend** | React dashboards, data visualization |
| 10 | **DevOps** | Docker, CI/CD, monitoring |

## Career Value

This single project prepares you for roles like:
- **Web Scraping Engineer**
- **Backend Developer**
- **Data Engineer**
- **Big Data Developer**
- **Cloud/AWS Engineer**
- **Full-Stack Developer**

---

# ✨ Core Features

## 1. Authentication & Session Management
```
┌─────────────────────────────────────────────────────────────┐
│ FEATURE: Multi-Account Authentication                       │
├─────────────────────────────────────────────────────────────┤
│ • Login with cookie persistence (no repeated logins)        │
│ • Session rotation between accounts                         │
│ • Credential encryption (AWS Secrets Manager)               │
│ • Automatic session refresh                                 │
│ • Proxy assignment per account                              │
└─────────────────────────────────────────────────────────────┘
```

## 2. Data Extraction
```
┌─────────────────────────────────────────────────────────────┐
│ FEATURE: Comprehensive Data Scraping                        │
├─────────────────────────────────────────────────────────────┤
│ PROFILES                                                    │
│ ├── Username, Full Name, Bio                                │
│ ├── Follower/Following/Post counts                          │
│ ├── Verification status, Privacy status                     │
│ ├── Category (Creator, Business, etc.)                      │
│ └── Profile picture URL                                     │
│                                                              │
│ POSTS                                                        │
│ ├── Post ID, Media type (image/video/carousel/reel)         │
│ ├── Caption text                                             │
│ ├── Hashtags & Mentions                                      │
│ ├── Like/Comment/Share counts                                │
│ ├── Location data                                            │
│ └── Timestamp                                                │
│                                                              │
│ STORIES                                                      │
│ ├── Story ID, Media type                                     │
│ ├── Duration (for videos)                                    │
│ ├── Interactive elements (polls, questions)                  │
│ ├── Music information                                        │
│ ├── Mentions & Hashtags                                      │
│ └── Expiration time                                          │
└─────────────────────────────────────────────────────────────┘
```

## 3. Media Downloads
```
┌─────────────────────────────────────────────────────────────┐
│ FEATURE: Complete Media Download Engine                     │
├─────────────────────────────────────────────────────────────┤
│ DOWNLOAD TYPES                                               │
│ ├── Profile Pictures (HD quality)                            │
│ ├── Post Images (all carousel items)                         │
│ ├── Post Videos (multiple qualities)                         │
│ ├── Reels (with audio)                                       │
│ ├── Stories (before expiry)                                  │
│ ├── Highlights                                               │
│ └── Audio extraction from Reels                              │
│                                                              │
│ CAPABILITIES                                                 │
│ ├── Parallel downloads (5 concurrent)                        │
│ ├── Resume interrupted downloads                             │
│ ├── Automatic S3 upload                                      │
│ ├── Organized folder structure                               │
│ └── Progress tracking                                        │
└─────────────────────────────────────────────────────────────┘
```

## 4. Safe Automation
```
┌─────────────────────────────────────────────────────────────┐
│ FEATURE: Human-Like Actions                                 │
├─────────────────────────────────────────────────────────────┤
│ ACTIONS SUPPORTED                                            │
│ ├── Follow/Unfollow (rate-limited)                           │
│ ├── Like posts (randomized)                                  │
│ ├── View stories (natural timing)                            │
│ ├── Scroll feed (human patterns)                             │
│ └── Save posts                                               │
│                                                              │
│ SAFETY MEASURES                                              │
│ ├── Daily/Hourly limits                                      │
│ ├── Random delays (15-45 sec)                                │
│ ├── Sleep hours (11 PM - 7 AM)                               │
│ ├── Account warmup protocol                                  │
│ ├── Automatic pause on warnings                              │
│ └── Risk score monitoring                                    │
└─────────────────────────────────────────────────────────────┘
```

## 5. Analytics & Insights
```
┌─────────────────────────────────────────────────────────────┐
│ FEATURE: Advanced Analytics                                 │
├─────────────────────────────────────────────────────────────┤
│ METRICS TRACKED                                              │
│ ├── Daily action counts                                      │
│ ├── Follow/Unfollow ratios                                   │
│ ├── Trending hashtags                                        │
│ ├── Engagement patterns                                      │
│ ├── Account health scores                                    │
│ └── Optimal action timing                                    │
│                                                              │
│ ML FEATURES                                                  │
│ ├── Similar account recommendations                          │
│ ├── Content suggestions                                      │
│ ├── Trend prediction                                         │
│ └── Risk/Ban probability                                     │
└─────────────────────────────────────────────────────────────┘
```

---

# 🔄 Complete Workflow

## How The System Works (Step-by-Step)

### Phase 1: Initialization
```
1. User starts the system via Dashboard
         │
         ▼
2. Django API receives "start bot" request
         │
         ▼
3. Celery worker picks up the task
         │
         ▼
4. Bot Controller initializes:
   ├── Load account credentials (from Secrets Manager)
   ├── Select proxy from pool
   ├── Configure browser fingerprint
   └── Check rate limits in Redis
```

### Phase 2: Browser Session
```
5. Playwright launches Chromium browser
         │
         ▼
6. Browser connects through proxy
         │
         ▼
7. Login flow:
   ├── Check for existing cookies
   │   ├── YES → Load cookies, verify session
   │   └── NO → Perform login, save cookies
         │
         ▼
8. Session established ✓
```

### Phase 3: Exploration & Actions
```
9. Exploration loop begins:
   │
   ├── SCROLL FEED
   │   ├── Scroll 300-700px (randomized)
   │   ├── Pause 2-5 seconds
   │   ├── Extract visible content
   │   └── Store hashtags, mentions
   │
   ├── VISIT PROFILES
   │   ├── Click on username
   │   ├── Extract profile data
   │   ├── Store in MongoDB
   │   └── Return to feed
   │
   ├── VIEW STORIES
   │   ├── Click story circle
   │   ├── Wait duration
   │   ├── Extract story data
   │   └── Next story or exit
   │
   ├── PERFORM ACTIONS (if limits allow)
   │   ├── Follow (8-15/day)
   │   ├── Like (10-20/hour)
   │   └── Log action to PostgreSQL
   │
   └── COOLDOWN
       ├── Random wait 15-45 min
       └── Check if sleep time
```

### Phase 4: Data Processing
```
10. Raw data flows to storage:
    │
    ├── PostgreSQL (structured data)
    │   └── Accounts, Sessions, Actions, Analytics
    │
    ├── MongoDB (document data)
    │   └── Profiles, Posts, Stories, Hashtags
    │
    ├── AWS S3 (media files)
    │   └── Images, Videos, Screenshots
    │
    └── Redis (real-time state)
        └── Rate limits, Session state, Counters
```

### Phase 5: Big Data Pipeline
```
11. Spark processes data (scheduled):
    │
    ├── BATCH JOBS (daily)
    │   ├── Aggregate daily stats
    │   ├── Calculate trending hashtags
    │   ├── Update account health scores
    │   └── Generate recommendations
    │
    └── STREAMING JOBS (real-time)
        ├── Live hashtag counting
        └── Anomaly detection
```

### Phase 6: Dashboard Updates
```
12. Frontend receives updates:
    │
    ├── WebSocket pushes real-time stats
    ├── REST API provides historical data
    └── User sees live bot activity
```

---

# 🧱 Technology Stack (Detailed)

## Complete Technology Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TECHNOLOGY STACK                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        FRONTEND LAYER                                │    │
│  │  React 18 │ Vite │ Recharts │ Socket.io-client │ Tailwind CSS       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         API LAYER                                    │    │
│  │  Django 4.2 │ Django REST Framework │ JWT Auth │ Celery 5.3         │    │
│  │  Node.js 20 │ Express │ Socket.io │ Bull (Queue)                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      AUTOMATION LAYER                                │    │
│  │  Playwright 1.40 │ Selenium 4.15 │ Scrapy 2.11 │ BeautifulSoup 4    │    │
│  │  Requests │ lxml │ Proxy Rotation │ Fingerprint Randomization       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        DATA LAYER                                    │    │
│  │  PostgreSQL 15 │ MongoDB 7 │ Redis 7 │ AWS S3                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      BIG DATA LAYER                                  │    │
│  │  Apache Spark 3.5 │ PySpark │ Spark SQL │ Spark Streaming           │    │
│  │  AWS Glue │ Databricks │ AWS DMS (CDC)                              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         ML LAYER                                     │    │
│  │  PySpark MLlib │ ALS Algorithm │ Scikit-learn │ Pandas              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        CLOUD LAYER                                   │    │
│  │  AWS EC2 │ AWS RDS │ AWS S3 │ AWS Lambda │ AWS Glue                 │    │
│  │  AWS ElastiCache │ AWS Secrets Manager │ AWS CloudWatch │ AWS VPC   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Why Each Technology?

| Technology | Purpose | Why Chosen |
|------------|---------|------------|
| **Playwright** | Browser automation | Best anti-detection, async support, reliable |
| **Selenium** | Learning tool | Industry standard, good for learning |
| **Scrapy** | Bulk scraping | Fast, built-in pipelines, scalable |
| **Django** | REST API | Mature, ORM, admin panel, ecosystem |
| **Node.js** | Real-time | Best for WebSockets, event-driven |
| **PostgreSQL** | Structured data | ACID compliance, reliability |
| **MongoDB** | Document data | Flexible schema, nested data |
| **Redis** | Caching/Queue | Speed, rate limiting, pub/sub |
| **Spark** | Big Data | Distributed processing, ML support |
| **AWS** | Cloud | Industry standard, comprehensive services |

---

# 📦 Module Documentation

## 1. Automation Module (`/automation`)

### 1.1 Browser Manager
```python
# File: automation/playwright/browser_manager.py
# Purpose: Control browser instances with anti-detection

class InstagramBrowser:
    """
    Production-grade browser automation for Instagram.
    
    Features:
    - Chromium browser with anti-detection flags
    - Cookie-based session persistence
    - Proxy support
    - Human-like behavior simulation
    
    Methods:
    - __init__(headless, proxy): Initialize browser
    - login(username, password): Authenticate
    - visit_profile(username): Navigate to profile
    - scroll_feed(count): Scroll with human patterns
    - close(): Clean shutdown
    """
```

### 1.2 Profile Extractor
```python
# File: automation/extractors/profile_extractor.py
# Purpose: Extract all profile data from Instagram pages

class ProfileExtractor:
    """
    Extract comprehensive profile data.
    
    Data Extracted:
    - Basic info: username, full_name, bio
    - Stats: followers, following, posts
    - Flags: is_verified, is_private, is_business
    - Media: profile_pic_url
    
    Methods:
    - extract_profile(username) -> dict
    - extract_posts(username, limit) -> list
    - save_to_mongodb(data) -> ObjectId
    """
```

### 1.3 Rate Limiter
```python
# File: automation/safety/rate_limiter.py
# Purpose: Control action frequency to avoid bans

class RateLimiter:
    """
    Redis-backed rate limiting system.
    
    Limits Enforced:
    - follows_per_day: 15
    - likes_per_hour: 20
    - stories_per_hour: 10
    
    Methods:
    - can_perform_action(action_type, account_id) -> bool
    - record_action(action_type, account_id)
    - get_remaining(action_type, account_id) -> int
    - is_sleep_time() -> bool
    """
```

### 1.4 Media Downloader
```python
# File: automation/downloader/media_downloader.py
# Purpose: Download all types of Instagram media

class MediaDownloader:
    """
    Download images, videos, reels, and stories.
    
    Capabilities:
    - Single image/video download
    - Carousel (multi-image) download
    - Bulk download with parallelism
    - S3 upload integration
    - Resume interrupted downloads
    
    Methods:
    - download_image(url, filename) -> filepath
    - download_video(url, quality) -> filepath
    - download_reel(url, with_audio) -> filepath
    - bulk_download(urls, parallel) -> list
    - upload_to_s3(filepath, bucket) -> s3_key
    """
```

---

## 2. Backend Module (`/backend`)

### 2.1 Django API Structure
```
backend/
├── api/
│   └── v1/
│       ├── accounts/     # Bot account CRUD
│       ├── bots/         # Bot control (start/stop)
│       ├── downloads/    # Download management
│       ├── analytics/    # Stats & insights
│       └── webhooks/     # Notifications
├── core/
│   ├── authentication.py # JWT auth
│   └── permissions.py    # RBAC
├── services/
│   ├── instagram.py      # IG business logic
│   └── scheduler.py      # Celery tasks
├── settings.py
├── urls.py
└── celery.py
```

### 2.2 Key API Endpoints
```
Authentication:
POST   /api/v1/auth/login/          # Get JWT token
POST   /api/v1/auth/refresh/        # Refresh token

Accounts:
GET    /api/v1/accounts/            # List all bot accounts
POST   /api/v1/accounts/            # Add new account
GET    /api/v1/accounts/{id}/       # Get account details
DELETE /api/v1/accounts/{id}/       # Remove account
GET    /api/v1/accounts/{id}/health/ # Account health score

Bots:
POST   /api/v1/bots/start/          # Start bot
POST   /api/v1/bots/stop/           # Stop bot
POST   /api/v1/bots/pause/          # Pause bot
GET    /api/v1/bots/status/         # Get bot status

Analytics:
GET    /api/v1/analytics/dashboard/ # Dashboard data
GET    /api/v1/analytics/trends/    # Trending hashtags
GET    /api/v1/analytics/export/    # Export CSV/JSON

Downloads:
POST   /api/v1/downloads/           # Queue download
GET    /api/v1/downloads/           # List downloads
GET    /api/v1/downloads/{id}/      # Download status
```

---

## 3. Big Data Module (`/spark_jobs`)

### 3.1 Batch Jobs
```python
# File: spark_jobs/batch/daily_aggregation.py
# Purpose: Calculate daily statistics

"""
Daily Aggregation Job

Runs: Every day at 6 AM
Input: Raw action logs from PostgreSQL
Output: Aggregated stats to daily_analytics table

Metrics Calculated:
- Total actions per account per day
- Success/failure rates
- Average session duration
- Profiles explored count
"""
```

### 3.2 Streaming Jobs
```python
# File: spark_jobs/streaming/hashtag_counter.py
# Purpose: Real-time hashtag trend tracking

"""
Live Hashtag Counter

Input: Kafka stream of scraped hashtags
Output: Real-time trending scores

Process:
1. Window: 5 minutes sliding, 1 minute interval
2. Count hashtag occurrences
3. Calculate trending score
4. Push to Redis for dashboard
"""
```

### 3.3 ML Pipeline
```python
# File: spark_jobs/ml/recommender.py
# Purpose: User recommendations using ALS

"""
ALS Recommendation Engine

Algorithm: Alternating Least Squares (Collaborative Filtering)

Input: User-Item engagement matrix
- Users: Bot accounts
- Items: Explored profiles
- Ratings: Engagement score (follows, likes, views)

Output: Top 10 recommended accounts to explore

Hyperparameters:
- rank: 50
- maxIter: 10
- regParam: 0.1
"""
```

---

# 📊 Data Flow

## Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                               DATA FLOW                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   SOURCES                    PROCESSING                    DESTINATIONS     │
│   ───────                    ──────────                    ────────────     │
│                                                                              │
│   ┌──────────┐              ┌──────────────┐              ┌──────────┐      │
│   │Instagram │──scrape─────►│  Playwright  │──extract────►│ MongoDB  │      │
│   │ (Target) │              │  (Browser)   │              │(profiles)│      │
│   └──────────┘              └──────────────┘              └──────────┘      │
│        │                           │                            │           │
│        │                           │                            ▼           │
│        │                    ┌──────────────┐              ┌──────────┐      │
│        │                    │   Scrapy     │──bulk───────►│ MongoDB  │      │
│        └────crawl──────────►│  (Spiders)   │              │ (posts)  │      │
│                             └──────────────┘              └──────────┘      │
│                                    │                            │           │
│                                    │                            ▼           │
│   ┌──────────┐              ┌──────────────┐              ┌──────────┐      │
│   │   Bot    │──actions────►│  Rate Limiter│──log───────►│PostgreSQL│      │
│   │ Actions  │              │   (Redis)    │              │ (logs)   │      │
│   └──────────┘              └──────────────┘              └──────────┘      │
│                                    │                            │           │
│                                    │                            ▼           │
│   ┌──────────┐              ┌──────────────┐              ┌──────────┐      │
│   │  Media   │──download───►│  Downloader  │──upload─────►│  AWS S3  │      │
│   │  URLs    │              │   Engine     │              │ (files)  │      │
│   └──────────┘              └──────────────┘              └──────────┘      │
│                                                                  │          │
│                                                                  ▼          │
│                             ┌──────────────┐              ┌──────────┐      │
│                             │ Apache Spark │◄──────ETL───│ All DBs  │      │
│                             │  (Batch/ML)  │              │          │      │
│                             └──────┬───────┘              └──────────┘      │
│                                    │                                        │
│                                    ▼                                        │
│                             ┌──────────────┐              ┌──────────┐      │
│                             │    ML        │──predict────►│Dashboard │      │
│                             │  Predictions │              │ (React)  │      │
│                             └──────────────┘              └──────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# 🗄️ Database Schema

## PostgreSQL Tables

```sql
-- Core operational data

bot_accounts          -- Bot credentials & status
├── id                SERIAL PRIMARY KEY
├── username          VARCHAR(50) UNIQUE
├── status            VARCHAR(20) [active/paused/banned]
├── trust_score       DECIMAL(3,2)
├── proxy_id          FK → proxies
├── cookies_json      JSONB
└── created_at        TIMESTAMP

sessions              -- Bot session tracking
├── id                SERIAL PRIMARY KEY
├── account_id        FK → bot_accounts
├── started_at        TIMESTAMP
├── ended_at          TIMESTAMP
├── actions_count     INTEGER
└── status            VARCHAR(20)

action_logs           -- Complete audit trail
├── id                SERIAL PRIMARY KEY
├── account_id        FK → bot_accounts
├── session_id        FK → sessions
├── action_type       VARCHAR(30)
├── target_username   VARCHAR(50)
├── success           BOOLEAN
└── created_at        TIMESTAMP

daily_analytics       -- Aggregated stats
├── id                SERIAL PRIMARY KEY
├── date              DATE
├── account_id        FK → bot_accounts
├── follows_count     INTEGER
├── likes_count       INTEGER
└── error_count       INTEGER
```

## MongoDB Collections

```javascript
// Flexible document storage

profiles: {
  username: String,
  full_name: String,
  bio: String,
  stats: {
    followers: Number,
    following: Number,
    posts: Number
  },
  flags: {
    is_verified: Boolean,
    is_private: Boolean
  },
  scraped_at: Date
}

posts: {
  post_id: String,
  owner_username: String,
  media_type: String,
  caption: String,
  hashtags: [String],
  mentions: [String],
  engagement: {
    likes: Number,
    comments: Number
  },
  scraped_at: Date
}

stories: {
  story_id: String,
  owner_username: String,
  media_type: String,
  interactive: {
    has_poll: Boolean,
    has_question: Boolean
  },
  expires_at: Date
}
```

---

# 🔐 Safety & Rate Limiting

## Rate Limit Configuration

```python
SAFE_LIMITS = {
    # Per Day
    "follows_per_day": {"min": 8, "max": 15},
    "unfollows_per_day": {"min": 5, "max": 10},
    "comments_per_day": {"min": 3, "max": 8},
    
    # Per Hour
    "likes_per_hour": {"min": 10, "max": 20},
    "stories_per_hour": {"min": 5, "max": 10},
    
    # Session
    "scroll_duration_sec": {"min": 120, "max": 300},
    "cooldown_min": {"min": 15, "max": 45},
    
    # Daily Schedule
    "sleep_start_hour": 23,  # 11 PM
    "sleep_end_hour": 7,     # 7 AM
    "active_hours_per_day": {"min": 2, "max": 6}
}
```

## Account Warmup Protocol

```
NEW ACCOUNT WARMUP SCHEDULE:

Week 1: Browse Only
├── Day 1-3: Just scroll feed, no actions
├── Day 4-5: View 5-10 stories
└── Day 6-7: Continue browsing

Week 2: Light Actions
├── Day 8-10: 2-3 follows per day
├── Day 11-12: 5-8 story views
└── Day 13-14: Add 5-10 likes

Week 3: Moderate Actions  
├── Day 15-18: 5-8 follows per day
├── Day 19-21: 10-15 story views
└── Add occasional comments

Week 4+: Full Limits
└── Gradually reach standard limits
```

## Risk Score Calculation

```python
def calculate_risk_score(account):
    """
    Calculate account ban risk (0-100)
    
    0-30:  Safe (green)
    31-60: Caution (yellow)
    61-80: Warning (orange)
    81-100: Danger (red)
    """
    score = 0
    
    # Account age factor (20%)
    if account.age_days < 30:
        score += 15
    elif account.age_days < 90:
        score += 8
    
    # Action frequency (25%)
    if account.actions_today > LIMITS["follows_per_day"]["max"]:
        score += 25
    
    # Error rate (20%)
    score += account.error_rate * 20
    
    # Unusual patterns (15%)
    if account.has_unusual_activity:
        score += 15
    
    # Proxy quality (10%)
    if account.proxy.failure_count > 3:
        score += 10
    
    # Session patterns (10%)
    if not account.follows_natural_schedule:
        score += 10
    
    return min(score, 100)
```

---

# ☁️ AWS Infrastructure

## Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         VPC (10.0.0.0/16)                           │   │
│   │                                                                      │   │
│   │   ┌─────────────────────┐    ┌─────────────────────┐                │   │
│   │   │   Public Subnet     │    │   Private Subnet    │                │   │
│   │   │   (10.0.1.0/24)     │    │   (10.0.2.0/24)     │                │   │
│   │   │                     │    │                     │                │   │
│   │   │  ┌──────────────┐   │    │  ┌──────────────┐   │                │   │
│   │   │  │ EC2: Bot     │   │    │  │ RDS:         │   │                │   │
│   │   │  │ t3.medium    │   │    │  │ PostgreSQL   │   │                │   │
│   │   │  │ + Playwright │   │    │  │ db.t3.micro  │   │                │   │
│   │   │  └──────────────┘   │    │  └──────────────┘   │                │   │
│   │   │                     │    │                     │                │   │
│   │   │  ┌──────────────┐   │    │  ┌──────────────┐   │                │   │
│   │   │  │ EC2: API     │   │    │  │ ElastiCache  │   │                │   │
│   │   │  │ t3.small     │   │    │  │ Redis        │   │                │   │
│   │   │  │ + Django     │   │    │  │ cache.t3.micro│  │                │   │
│   │   │  └──────────────┘   │    │  └──────────────┘   │                │   │
│   │   │                     │    │                     │                │   │
│   │   └─────────────────────┘    └─────────────────────┘                │   │
│   │              ↑                                                       │   │
│   │              │                                                       │   │
│   │         ┌────┴────┐                                                  │   │
│   │         │   IGW   │ ← Internet Gateway                               │   │
│   │         └─────────┘                                                  │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│   │    S3      │  │   Lambda   │  │   Glue     │  │ CloudWatch │           │
│   │ (Storage)  │  │ (Serverless)│ │ (ETL)      │  │ (Logs)     │           │
│   └────────────┘  └────────────┘  └────────────┘  └────────────┘           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Cost Estimate

| Service | Configuration | Monthly Cost |
|---------|---------------|--------------|
| EC2 (Bot) | t3.medium, 24/7 | ~$30 |
| EC2 (API) | t3.small, 24/7 | ~$15 |
| RDS | db.t3.micro, PostgreSQL | ~$15 |
| ElastiCache | cache.t3.micro, Redis | ~$12 |
| S3 | 50GB Standard | ~$2 |
| Secrets Manager | 5 secrets | ~$2 |
| CloudWatch | Basic | ~$5 |
| **TOTAL** | | **~$82/month** |

---

# 🚀 Installation Guide

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- Git
- Conda (recommended) or pip

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/insta-edu-bot.git
cd insta-edu-bot

# 2. Create Conda environment
conda create -n insta-bot python=3.11 -y
conda activate insta-bot

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium

# 5. Start databases with Docker
docker-compose up -d

# 6. Initialize databases
python automation/database/postgres_setup.py
python automation/database/mongo_setup.py

# 7. Run migrations
cd backend
python manage.py migrate

# 8. Start the Django server
python manage.py runserver

# 9. (New terminal) Start Celery worker
celery -A backend worker -l info
```

## Verify Installation

```bash
# Test database connections
python automation/db_test.py

# Run first scraper
python automation/basic_scraper.py

# Test browser automation
python automation/playwright/browser_manager.py
```

---

# 💡 Usage Examples

## Basic Scraping

```python
from automation.extractors.profile_extractor import ProfileExtractor

# Initialize extractor
extractor = ProfileExtractor()

# Scrape a profile
data = extractor.extract_profile("instagram")
print(data)

# Save to database
extractor.save_to_mongodb(data)

# Cleanup
extractor.close()
```

## Downloading Media

```python
from automation.downloader.media_downloader import MediaDownloader

# Initialize downloader
downloader = MediaDownloader(download_dir="downloads")

# Download single image
downloader.download_image(
    url="https://example.com/image.jpg",
    filename="my_image.jpg"
)

# Bulk download
urls = ["url1", "url2", "url3"]
downloader.bulk_download(urls, prefix="batch")
```

## Rate-Limited Actions

```python
from automation.safety.rate_limiter import RateLimiter

# Initialize limiter
limiter = RateLimiter()

# Check if action is allowed
if limiter.can_perform_action("follows", account_id="acc1"):
    # Perform follow action
    perform_follow(target_user)
    limiter.record_action("follows", "acc1")
else:
    print("Rate limit reached, waiting...")
```

---

# 📁 Project Structure

```
insta-edu-bot/
│
├── 📂 automation/                   # Core bot engine
│   ├── 📂 playwright/              # Browser automation
│   │   ├── browser_manager.py      # Browser lifecycle
│   │   ├── fingerprint.py          # Anti-detection
│   │   └── proxy.py                # Proxy rotation
│   ├── 📂 scrapy_project/          # Bulk scraping
│   │   └── spiders/                # Scrapy spiders
│   ├── 📂 selenium/                # Learning tool
│   │   └── basic_driver.py
│   ├── 📂 extractors/              # Data extraction
│   │   ├── profile_extractor.py
│   │   ├── post_extractor.py
│   │   └── story_extractor.py
│   ├── 📂 downloader/              # Media downloads
│   │   ├── media_downloader.py
│   │   └── s3_uploader.py
│   ├── 📂 safety/                  # Rate limiting
│   │   ├── rate_limiter.py
│   │   ├── warmup.py
│   │   └── risk_scorer.py
│   ├── 📂 database/                # DB setup scripts
│   │   ├── postgres_setup.py
│   │   └── mongo_setup.py
│   └── basic_scraper.py            # Simple starter
│
├── 📂 backend/                      # Django API
│   ├── 📂 api/v1/                  # REST endpoints
│   ├── 📂 core/                    # Auth & permissions
│   ├── 📂 services/                # Business logic
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── manage.py
│
├── 📂 node_services/                # Node.js services
│   ├── 📂 websocket/               # Real-time server
│   ├── 📂 mongodb/                 # MongoDB operations
│   └── 📂 workers/                 # Background jobs
│
├── 📂 spark_jobs/                   # Big Data
│   ├── 📂 batch/                   # Daily ETL
│   ├── 📂 streaming/               # Real-time
│   └── 📂 ml/                      # ML pipelines
│
├── 📂 frontend/                     # React dashboard
│   ├── 📂 src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
│   └── package.json
│
├── 📂 infra/                        # Infrastructure
│   ├── 📂 terraform/               # AWS IaC
│   ├── 📂 docker/                  # Containers
│   └── 📂 scripts/                 # Deploy scripts
│
├── 📂 tests/                        # Test suites
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── 📂 docs/                         # Documentation
│   ├── COMPLETE_ROADMAP.md
│   ├── START_HERE_GUIDE.md
│   └── API.md
│
├── docker-compose.yml               # Local services
├── requirements.txt                 # Python deps
├── .env.example                     # Environment template
└── README.md                        # This file
```

---

# 🤝 Contributing

This is a personal educational project. However, if you'd like to learn alongside:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

# ⚖️ License & Disclaimer

## License

MIT License - Feel free to use for learning purposes.

## ⚠️ Important Disclaimer

```
THIS PROJECT IS FOR EDUCATIONAL PURPOSES ONLY.

1. Only use with accounts YOU own
2. Only use with dummy/test accounts
3. Never use for commercial purposes
4. Never use on production Instagram accounts
5. Always respect Instagram's Terms of Service
6. The author is not responsible for any misuse

By using this project, you agree to these terms.
```

---

<p align="center">
  <strong>Happy Learning! 🚀</strong><br>
  Built for education. Use responsibly.
</p>
