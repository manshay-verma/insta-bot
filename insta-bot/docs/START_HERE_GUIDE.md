# 🚦 WHERE TO START - PRACTICAL BUILD GUIDE
## Day-by-Day Implementation Steps

> **Required Python Version:** 🐍 **Python 3.11+** (Highly recommended for stability and library support)

> This guide tells you **EXACTLY** what to build, in what order, and why.

---

# 🎯 THE STARTING POINT

## START HERE → Day 1, Task 1

```
Your FIRST action should be:
┌─────────────────────────────────────────────────────────────┐
│  1. Create the project folder structure                     │
│  2. Set up Python virtual environment                       │
│  3. Build your FIRST working scraper                        │
└─────────────────────────────────────────────────────────────┘
```

---

# 📍 BUILD ORDER (Why This Order?)

```
PHASE 1: Local Development (Weeks 1-4)
├── Step 1: Basic scraping works locally ✓
├── Step 2: Data flows into local database ✓
├── Step 3: Simple automation running ✓
└── Step 4: Downloads work locally ✓

PHASE 2: Add Backend (Weeks 5-6)
├── Step 5: Django API controls everything ✓
└── Step 6: Node.js for real-time ✓

PHASE 3: Cloud Migration (Weeks 7-8)
├── Step 7: Move to AWS ✓
└── Step 8: Everything runs on cloud ✓

PHASE 4: Advanced Features (Weeks 9-12)
├── Step 9: Big Data pipeline ✓
├── Step 10: ML/Recommendations ✓
└── Step 11: Full dashboard ✓
```

---

# 🚀 WEEK 1: YOUR FIRST WORKING CODE

## Day 1: Project Setup (2-3 hours)

### Task 1.1: Create Folder Structure
```bash
# Run these commands
mkdir insta-edu-bot
cd insta-edu-bot

# Create folder structure
mkdir -p automation/{scrapy_project,playwright,selenium,downloader,safety}
mkdir -p backend/{api,accounts,downloads,analytics}
mkdir -p node_services/{websocket,mongodb,workers}
mkdir -p spark_jobs/{batch,streaming,ml}
mkdir -p frontend/src
mkdir -p infra/{terraform,docker,scripts}
mkdir -p tests/{unit,integration,e2e}
mkdir docs
```

### Task 1.2: Set Up Python Environment

Choose **ONE** of the following methods:

#### Method A: Using Conda (Recommended if you have Conda installed)
```bash
# Create a new environment with Python 3.11
conda create -n insta-bot python=3.11 -y

# Activate the environment
conda activate insta-bot
```

#### Method B: Using venv (Standard Python)
```bash
# Create virtual environment
python -m venv venv

# Activate it (Windows)
.\venv\Scripts\activate

# Activate it (Mac/Linux)
source venv/bin/activate
```

# Create requirements.txt

### Task 1.3: Create requirements.txt
```
# requirements.txt - Start with basics, add more as needed

# Web Scraping
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.3
scrapy==2.11.0
selenium==4.15.2
playwright==1.40.0

# Django Backend
django==4.2.7
djangorestframework==3.14.0

# Databases
psycopg2-binary==2.9.9
pymongo==4.6.0

# Task Queue
celery==5.3.4
redis==5.0.1

# AWS
boto3==1.33.0

# Utilities
python-dotenv==1.0.0
pydantic==2.5.2
```

### Task 1.4: Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

✅ **END OF DAY 1**: You have a project structure ready!

---

## Day 2: YOUR FIRST SCRAPER (3-4 hours)

### Task 2.1: Start Simple - Requests + BeautifulSoup
```python
# File: automation/basic_scraper.py
# This is your FIRST working code!

import requests
from bs4 import BeautifulSoup

def scrape_public_profile(username):
    """
    Scrape basic public profile info
    START HERE - This is the simplest scraper
    """
    url = f"https://www.instagram.com/{username}/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Extract title (contains username)
        title = soup.find('title')
        
        print(f"✅ Successfully scraped: {username}")
        print(f"📄 Title: {title.text if title else 'Not found'}")
        
        return {
            "username": username,
            "title": title.text if title else None,
            "status": "success"
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"username": username, "status": "error", "error": str(e)}

# Test it!
if __name__ == "__main__":
    result = scrape_public_profile("instagram")  # Official Instagram account
    print(result)
```

### Task 2.2: Run Your First Scraper
```bash
cd automation
python basic_scraper.py
```

✅ **If this works, you've started!**

---

## Day 3: Selenium (Learning Browser Automation)

### Task 3.1: Basic Selenium Script
```python
# File: automation/selenium/basic_driver.py
# Learning Selenium - Browser automation basics

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class SeleniumLearning:
    """
    Use this to LEARN Selenium basics
    Later we'll switch to Playwright for production
    """
    
    def __init__(self, headless=False):
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
    
    def visit_profile(self, username):
        """Visit a public Instagram profile"""
        url = f"https://www.instagram.com/{username}/"
        
        print(f"🌐 Navigating to {url}")
        self.driver.get(url)
        
        # Wait for page to load
        time.sleep(3)
        
        # Get page title
        title = self.driver.title
        print(f"📄 Page Title: {title}")
        
        # Take screenshot
        self.driver.save_screenshot(f"screenshot_{username}.png")
        print(f"📸 Screenshot saved!")
        
        return title
    
    def close(self):
        self.driver.quit()

# Test it
if __name__ == "__main__":
    bot = SeleniumLearning(headless=False)  # Set True to hide browser
    try:
        bot.visit_profile("instagram")
        input("Press Enter to close...")
    finally:
        bot.close()
```

✅ **END OF DAY 3**: You understand browser automation!

---

## Day 4: Playwright (Production Automation)

### Task 4.1: Playwright Setup
```python
# File: automation/playwright/browser_manager.py
# This is what we'll use in PRODUCTION

from playwright.sync_api import sync_playwright
import time
import random

class InstagramBrowser:
    """
    Production-grade browser automation
    Better than Selenium for anti-detection
    """
    
    def __init__(self, headless=False):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox'
            ]
        )
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.page = self.context.new_page()
    
    def human_delay(self, min_sec=1, max_sec=3):
        """Random delay to appear human"""
        time.sleep(random.uniform(min_sec, max_sec))
    
    def visit_profile(self, username):
        """Visit a profile with human-like behavior"""
        url = f"https://www.instagram.com/{username}/"
        
        print(f"🌐 Visiting {username}...")
        self.page.goto(url)
        self.human_delay(2, 4)
        
        # Extract page title
        title = self.page.title()
        print(f"📄 Title: {title}")
        
        # Take screenshot
        self.page.screenshot(path=f"playwright_{username}.png")
        print(f"📸 Screenshot saved!")
        
        return {"username": username, "title": title}
    
    def scroll_page(self, scroll_count=3):
        """Scroll like a human"""
        for i in range(scroll_count):
            scroll_amount = random.randint(300, 700)
            self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            self.human_delay(0.5, 1.5)
            print(f"📜 Scrolled {i+1}/{scroll_count}")
    
    def close(self):
        self.browser.close()
        self.playwright.stop()

# Test it
if __name__ == "__main__":
    bot = InstagramBrowser(headless=False)
    try:
        bot.visit_profile("instagram")
        bot.scroll_page(5)
        input("Press Enter to close...")
    finally:
        bot.close()
```

✅ **END OF DAY 4**: You have production-ready browser automation!

---

## Day 5: Local Database Setup

### Task 5.1: Start PostgreSQL with Docker
```bash
# Create docker-compose.yml in project root
```

### Task 5.2: docker-compose.yml
```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: instabot_postgres
    environment:
      POSTGRES_USER: instabot
      POSTGRES_PASSWORD: instabot123
      POSTGRES_DB: instabot_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  mongodb:
    image: mongo:7
    container_name: instabot_mongo
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  redis:
    image: redis:7-alpine
    container_name: instabot_redis
    ports:
      - "6379:6379"

volumes:
  postgres_data:
  mongo_data:
```

### Task 5.3: Start Databases
```bash
docker-compose up -d
```

### Task 5.4: Test Database Connections
```python
# File: automation/db_test.py
# Test all database connections

# PostgreSQL
import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        database="instabot_db",
        user="instabot",
        password="instabot123"
    )
    print("✅ PostgreSQL connected!")
    conn.close()
except Exception as e:
    print(f"❌ PostgreSQL error: {e}")

# MongoDB
from pymongo import MongoClient

try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client.instabot
    print("✅ MongoDB connected!")
    client.close()
except Exception as e:
    print(f"❌ MongoDB error: {e}")

# Redis
import redis

try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.ping()
    print("✅ Redis connected!")
except Exception as e:
    print(f"❌ Redis error: {e}")
```

✅ **END OF DAY 5**: Databases running locally!

---

## Day 6-7: Scrapy Spider

### Task 6.1: Create Scrapy Project
```bash
cd automation
scrapy startproject scrapy_project
cd scrapy_project
scrapy genspider instagram_spider instagram.com
```

### Task 6.2: Basic Spider
```python
# File: automation/scrapy_project/scrapy_project/spiders/instagram_spider.py

import scrapy
import json

class InstagramSpider(scrapy.Spider):
    name = 'instagram_spider'
    
    def __init__(self, usernames=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usernames = usernames.split(',') if usernames else ['instagram']
    
    def start_requests(self):
        for username in self.usernames:
            url = f'https://www.instagram.com/{username}/'
            yield scrapy.Request(url, callback=self.parse, meta={'username': username})
    
    def parse(self, response):
        username = response.meta['username']
        
        yield {
            'username': username,
            'title': response.css('title::text').get(),
            'url': response.url,
            'status': response.status
        }
```

### Task 6.3: Run Spider
```bash
scrapy crawl instagram_spider -a usernames="instagram,cristiano" -o results.json
```

✅ **END OF WEEK 1**: You have working scrapers!

---

# 🚀 WEEK 2: DATA STORAGE & EXTRACTION

## Day 8-9: PostgreSQL Models

### Task 8.1: Create Database Tables
```python
# File: automation/database/postgres_setup.py

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connect
conn = psycopg2.connect(
    host="localhost",
    database="instabot_db",
    user="instabot",
    password="instabot123"
)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cursor = conn.cursor()

# Create tables
tables = """
-- Bot Accounts
CREATE TABLE IF NOT EXISTS bot_accounts (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Scraped Profiles
CREATE TABLE IF NOT EXISTS profiles (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(150),
    bio TEXT,
    followers INTEGER,
    following INTEGER,
    posts_count INTEGER,
    is_private BOOLEAN DEFAULT false,
    scraped_at TIMESTAMP DEFAULT NOW()
);

-- Action Logs
CREATE TABLE IF NOT EXISTS action_logs (
    id SERIAL PRIMARY KEY,
    action_type VARCHAR(30) NOT NULL,
    target_username VARCHAR(50),
    success BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Downloads
CREATE TABLE IF NOT EXISTS downloads (
    id SERIAL PRIMARY KEY,
    media_type VARCHAR(20),
    source_url TEXT,
    local_path TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);
"""

for statement in tables.split(';'):
    if statement.strip():
        cursor.execute(statement)
        
print("✅ All tables created!")

cursor.close()
conn.close()
```

✅ **Run this to create your database schema!**

---

## Day 10-11: MongoDB Setup

### Task 10.1: MongoDB Collections
```python
# File: automation/database/mongo_setup.py

from pymongo import MongoClient
from datetime import datetime

# Connect
client = MongoClient("mongodb://localhost:27017/")
db = client.instabot

# Create collections with sample documents
# Profiles (flexible schema)
db.profiles.insert_one({
    "username": "test_user",
    "full_name": "Test User",
    "bio": "This is a test bio",
    "stats": {
        "followers": 1000,
        "following": 500,
        "posts": 100
    },
    "scraped_at": datetime.now()
})
print("✅ Profiles collection ready!")

# Posts (nested data)
db.posts.insert_one({
    "post_id": "abc123",
    "owner": "test_user",
    "media_type": "image",
    "caption": "Test post #test",
    "hashtags": ["test"],
    "engagement": {
        "likes": 100,
        "comments": 10
    },
    "scraped_at": datetime.now()
})
print("✅ Posts collection ready!")

# Create indexes
db.profiles.create_index("username", unique=True)
db.posts.create_index("post_id", unique=True)
db.posts.create_index("owner")
print("✅ Indexes created!")

client.close()
```

---

## Day 12-14: Complete Extractor

### Task 12.1: Profile Data Extractor
```python
# File: automation/extractors/profile_extractor.py

from playwright.sync_api import sync_playwright
from datetime import datetime
import json
import re

class ProfileExtractor:
    """Extract all profile data"""
    
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()
    
    def extract_profile(self, username):
        """Extract profile data from Instagram"""
        url = f"https://www.instagram.com/{username}/"
        self.page.goto(url)
        self.page.wait_for_load_state("networkidle")
        
        # Get page content
        content = self.page.content()
        
        # Extract data from meta tags
        profile_data = {
            "username": username,
            "scraped_at": datetime.now().isoformat(),
            "url": url
        }
        
        # Try to extract from page
        try:
            # Title contains name
            title = self.page.title()
            profile_data["title"] = title
            
            # Meta description often has follower info
            meta = self.page.locator('meta[property="og:description"]').get_attribute('content')
            if meta:
                profile_data["meta_description"] = meta
                
                # Parse follower counts from description
                numbers = re.findall(r'([\d,]+)', meta)
                if len(numbers) >= 2:
                    profile_data["followers_text"] = numbers[0]
                    profile_data["following_text"] = numbers[1]
                    
        except Exception as e:
            profile_data["error"] = str(e)
        
        return profile_data
    
    def save_to_file(self, data, filename):
        """Save extracted data to JSON file"""
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"💾 Saved to {filename}")
    
    def close(self):
        self.browser.close()
        self.playwright.stop()

# Test
if __name__ == "__main__":
    extractor = ProfileExtractor()
    try:
        data = extractor.extract_profile("instagram")
        print(json.dumps(data, indent=2, default=str))
        extractor.save_to_file(data, "profile_instagram.json")
    finally:
        extractor.close()
```

✅ **END OF WEEK 2**: Data extraction working!

---

# 🚀 WEEK 3-4: DOWNLOADS & SAFETY

## Day 15-17: Download Engine

### Task 15.1: Image/Video Downloader
```python
# File: automation/downloader/media_downloader.py

import requests
import os
from pathlib import Path
from datetime import datetime

class MediaDownloader:
    """Download images and videos from Instagram"""
    
    def __init__(self, download_dir="downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def download_image(self, url, filename=None):
        """Download single image"""
        if not filename:
            filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        filepath = self.download_dir / filename
        
        try:
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Downloaded: {filename}")
            return str(filepath)
            
        except Exception as e:
            print(f"❌ Download failed: {e}")
            return None
    
    def download_video(self, url, filename=None):
        """Download video"""
        if not filename:
            filename = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        
        return self.download_image(url, filename)  # Same logic
    
    def bulk_download(self, urls, prefix="media"):
        """Download multiple files"""
        results = []
        for i, url in enumerate(urls):
            filename = f"{prefix}_{i+1}.jpg"
            result = self.download_image(url, filename)
            results.append(result)
        return results

# Test
if __name__ == "__main__":
    downloader = MediaDownloader()
    # Test with a public image URL
    test_url = "https://via.placeholder.com/500"  # Replace with actual URL
    downloader.download_image(test_url, "test_image.jpg")
```

---

## Day 18-21: Rate Limiter

### Task 18.1: Safety Controller
```python
# File: automation/safety/rate_limiter.py

import redis
import time
from datetime import datetime, timedelta
import random

class RateLimiter:
    """Control action rates to avoid bans"""
    
    # Safe limits
    LIMITS = {
        "follows_per_day": 15,
        "likes_per_hour": 20,
        "stories_per_hour": 10,
        "scrolls_per_session": 50
    }
    
    def __init__(self, redis_host='localhost', redis_port=6379):
        self.redis = redis.Redis(host=redis_host, port=redis_port, db=0)
    
    def can_perform_action(self, action_type, account_id):
        """Check if action is allowed"""
        key = f"ratelimit:{account_id}:{action_type}"
        
        # Get limit for this action
        limit_key = f"{action_type}_per_hour" if "hour" in str(self.LIMITS.get(f"{action_type}_per_hour")) else f"{action_type}_per_day"
        limit = self.LIMITS.get(limit_key, 10)
        
        # Check current count
        current = self.redis.get(key)
        current = int(current) if current else 0
        
        if current >= limit:
            print(f"⚠️ Rate limit reached for {action_type}")
            return False
        
        return True
    
    def record_action(self, action_type, account_id):
        """Record an action"""
        key = f"ratelimit:{account_id}:{action_type}"
        
        # Increment counter
        self.redis.incr(key)
        
        # Set expiry (1 hour for hourly, 24 hours for daily)
        if "hour" in action_type:
            self.redis.expire(key, 3600)  # 1 hour
        else:
            self.redis.expire(key, 86400)  # 24 hours
    
    def get_random_delay(self, min_sec=15, max_sec=45):
        """Get random delay between actions"""
        delay = random.uniform(min_sec, max_sec)
        print(f"⏳ Waiting {delay:.1f} seconds...")
        return delay
    
    def is_sleep_time(self):
        """Check if it's sleep hours (11 PM - 7 AM)"""
        hour = datetime.now().hour
        if hour >= 23 or hour < 7:
            print("😴 Sleep time - no actions allowed")
            return True
        return False

# Test
if __name__ == "__main__":
    limiter = RateLimiter()
    
    account_id = "test_account"
    
    # Simulate actions
    for i in range(20):
        if limiter.can_perform_action("follows", account_id):
            print(f"✅ Action {i+1} allowed")
            limiter.record_action("follows", account_id)
        else:
            print(f"❌ Action {i+1} blocked")
        
        time.sleep(0.1)  # Small delay for testing
```

✅ **END OF WEEK 4**: Safe automation system ready!

---

# 📋 QUICK REFERENCE: BUILD ORDER

```
WEEK 1
├── Day 1: Project structure + Python environment
├── Day 2: First Requests + BeautifulSoup scraper
├── Day 3: Selenium basics (learning)
├── Day 4: Playwright setup (production)
├── Day 5: Docker + PostgreSQL + MongoDB + Redis
├── Day 6-7: Scrapy spider

WEEK 2
├── Day 8-9: PostgreSQL schema
├── Day 10-11: MongoDB setup
├── Day 12-14: Profile data extractor

WEEK 3
├── Day 15-17: Download engine
├── Day 18-21: Rate limiter + safety

WEEK 4
├── Day 22-24: Django backend setup
├── Day 25-28: REST APIs

WEEK 5-6
├── Node.js WebSocket server
├── Real-time monitoring

WEEK 7-8
├── AWS migration
├── S3 storage

WEEK 9-10
├── PySpark setup
├── ETL pipelines

WEEK 11-12
├── ML recommendations
├── React dashboard
```

---

# 🎯 YOUR FIRST 7 COMMANDS

Run these IN ORDER to start building:

```bash
# 1. Create project
mkdir insta-edu-bot && cd insta-edu-bot

# 2. Create virtual environment
python -m venv venv && .\venv\Scripts\activate

# 3. Create requirements.txt and install
pip install requests beautifulsoup4 playwright psycopg2-binary pymongo redis

# 4. Install Playwright browser
playwright install chromium

# 5. Start databases
docker-compose up -d

# 6. Create your first scraper file
# (Copy the basic_scraper.py code from Day 2)

# 7. Run it!
python automation/basic_scraper.py
```

---

# ✅ SUCCESS CHECKLIST

Mark each as you complete:

```
WEEK 1
[ ] Project folder created
[ ] Python venv activated
[ ] First scraper (Requests) works
[ ] Selenium script runs
[ ] Playwright script runs
[ ] Docker databases running
[ ] Scrapy spider works

WEEK 2
[ ] PostgreSQL tables created
[ ] MongoDB collections ready
[ ] Profile extractor works
[ ] Data saved to database

WEEK 3-4
[ ] Download engine works
[ ] Rate limiter active
[ ] Safety checks in place

And continue...
```

---

> **START WITH DAY 1, TASK 1. Don't skip ahead!**
> Each step builds on the previous one.
