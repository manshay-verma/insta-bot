# Automation Module Overview

## 📁 What is the `automation` folder?

The `automation` folder is the core engine of the `insta-bot` project responsible for all direct interactions with Instagram. Rather than using official APIs (which are highly restrictive), this module simulates human behavior using actual browsers and web scrapers to perform actions, extract data, and download media safely.

## 🏗️ Structure and Sub-modules

The folder is divided into specialized sub-modules, each handling a distinct part of the automation pipeline:

### 1. `playwright_engine/` (Primary Engine)

This is the main driver for logged-in automation interactions.

* **Purpose:** Uses Playwright to simulate a real user browsing Instagram.
* **Key Work:** Authentication (login, cookies, 2FA), Navigation (scrolling, clicking), Actions (Liking, following, commenting, saving posts), and Data Extraction (reading bios, posts, metrics).

### 2. `safety/` (Anti-Ban System)

A critical module to ensure the bot accounts remain healthy and avoid action blocks.

* **Purpose:** Simulates human usage patterns to bypass detection.
* **Key Work:** Implements rate limits (actions per hour/day), random delay generators (human-like pauses), sleep hours, account risk scoring, and auto-pause mechanisms upon detecting warnings.

### 3. `downloader/` (Media Manager)

Responsible for reliably downloading various media formats from the platform.

* **Purpose:** Fetches static and dynamic content.
* **Key Work:** Downloading single posts, videos, carousels, reels (with audio), stories, and HD profile pictures. It handles bulk parallel downloads and supports resuming interrupted downloads.

### 4. `scrapy_project/` (Bulk Data Scraper)

* **Purpose:** High-speed data extraction for public information without requiring interactive browser sessions.
* **Key Work:** Spiders for grabbing hashtag feeds, public profile data, comments, and follower lists. Features request throttling and proxy rotation.

### 5. `selenium_engine/` (Fallback Engine)
    
* **Purpose:** A backup web automation framework.
* **Key Work:** Setup to take over basic navigation and interactions if the Playwright engine fails or encounters specific anti-bot countermeasures that Selenium's stealth profiles can bypass better.

---

## 🚀 Status of Work in our Project

According to the latest documentation and roadmap, development of the `automation` module is **100% complete**.

**Work Completed Summary:**

* **Playwright Engine:** 22/22 Tasks completed
* **Downloader:** 12/12 Tasks completed
* **Safety System:** 12/12 Tasks completed
* **Scrapy Project:** 8/8 Tasks completed
* **Selenium Fallback:** 6/6 Tasks completed
* **Grand Total:** 60/60 features successfully implemented.

The current state of the backend is fully equipped to safely browse, interact, and scrape data from Instagram through our implemented automation orchestrations.



Prompt for next phase:
we want to add sent phase in that phase we created to behave of views and reactions we repost the photos and reels on the specific account com and add more functionality according to you and make complete task and md for understanding