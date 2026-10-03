# InstaBot Repo Explanation (Hinglish, Actual Repo Flow)

## 1. Repo ka Overview
Yeh repo ek Instagram automation aur scraping platform hai jisme backend, browser automation, media download, orchestration, aur docs sab included hain. Main objective hai:
- Instagram ke data aur media ko automate karke collect karna
- multiple bot accounts aur proxies ke saath safe session maintain karna
- download tasks manage karna
- analytics aur action logging backend se provide karna
- future big-data / cloud deployment ke liye ready architecture rakhna

## 2. Repo Structure
Repo ke important folders:
- `automation/` - browser automation aur downloader code
  - `playwright_engine/` - Playwright browser manager aur Instagram navigation logic
  - `downloader/` - media downloader logic
  - `safety/` - rate limiting aur behavior policies
  - `selenium/` - Selenium based support (secondary engine)
- `backend/` - Django REST API aur database models
  - `account/`, `analytics/`, `downloads/`, `cookies/`, `core/`, `services/`
- `orchestrator/` - bot worker orchestration aur backend integration
- `docs/` - project roadmap aur documentation
- `frontend/` - React/Vite dashboard code (not deeply inspected but present)
- `node_service/` - websocket / realtime service logic
- `spark_jobs/` - Spark data processing / ML pipeline support
- `infradocker/`, `infrascripts/`, `infraterraform/` - deployment and infra automation

## 3. Main Kaam ka Flow
### 3.1 Frontend se backend tak
- User frontend se request bhejta hai, jaise `start bot`, `download URLs`, `get analytics`.
- Backend Django API us request ko receive karde hai.
- Backend account/proxy data use karke orkhestration worker task fire karta hai.

### 3.2 Orchestrator aur worker
- `orchestrator/bot_worker.py` ka `BotWorker` class actual bot session chalata hai.
- Worker backend se account details fetch karta hai (`InstaApiClient.get_account`).
- Use proxy settings aur cookies data milti hain.
- Worker session start/stop karwata hai backend pe.
- Browser start karne ke liye `automation/playwright_engine/browser_manager.py` se `InstagramBrowser` class use hoti hai.

### 3.3 Browser automation aur login
- `InstagramBrowser` Playwright launch karta hai with stealth arguments.
- Human-like typing, scrolling, mouse movement simulate hoti hai.
- Cookies ko backend se `CookieSync` se load karke browser context me add kiya jata hai.
- Agar cookies valid hain to cookie login hoti hai, otherwise fresh login attempt hota hai.
- 2FA / verification prompts handle karne ki logic bhi available hai.

### 3.4 Scraping aur actions
- Instagram profile visit karne se profile data extract hota hai.
- `extract_profile_info()` profile name, bio, followers, following, post count, profile pic, verified/private flags nikalta hai.
- Search, explore, feed scroll, navigation etc. automation engine mein available hai.
- Worker actions jaise follow, like, scrape, download, story view backend me `ActionCallback` se log hoti hain.

### 3.5 Media download
- `automation/downloader/media_downloader.py` multiple media download methods provide karta hai:
  - `download_image()`
  - `download_video()`
  - `download_reel()`
  - `download_story()`
  - `download_carousel()`
  - `bulk_download()`
- Ye downloader resume support, extension detection, organized folders, parallel downloading aur optional S3 upload bhi handle karta hai.

### 3.6 Cookie sync
- `orchestrator/cookie_sync.py` browser cookies ko backend me save/restore karta hai.
- `load_from_backend()` backend se cookies fetch karta hai.
- `save_to_backend()` browser se naye cookies backend me update karta hai.
- `export_to_file()` cookies Playwright-compatible JSON file banata hai.

## 4. Backend ka Role
Backend mainly API provider hai. Important cheezein:
- `backend/README.md` me API guide documented hai.
- APIs include bot account management, proxy registration, bot control, download queue, analytics, rate limits.
- `InstaApiClient` backend integration ka HTTP wrapper hai, jo worker aur orchestrator use karte hain.
- Backend se session start/stop, account health, cookie update, and action logging hota hai.

## 5. Actual Repo Behavior
### 5.1 Bot session lifecycle
1. `BotWorker.run()` call hota hai with task config.
2. Worker account details fetch karta hai from backend.
3. `start_session()` backend ko bolta hai session start karne ke liye.
4. Browser start hota hai `InstagramBrowser.start()` se.
5. Login attempt hota hai via cookies or password.
6. Requested task execute hota hai (scrape profile, download media, like posts, follow users, etc.).
7. Action log `ActionCallback` se backend me record hoti hai.
8. Cookies sync ki jati hain backend ke saath.
9. Session stop hota hai backend pe.

### 5.2 Media workflow
- `media_downloader.py` direct media URL se HTTP stream request karta hai.
- `download_carousel()` carousel ke items ko ordered list me download karta hai.
- `bulk_download()` multiple requests parallel me chalata hai for speed.
- Agar server `Range` support deta hai to interrupted downloads resume ho sakti hain.
- Optional `upload_to_s3()` method available hai agar `boto3` install ho.

### 5.3 Automation polish
- Playwright browser me anti-detection scripts add kiye gaye hain.
- `webdriver` property hide, `navigator.languages`, `navigator.platform`, `WebGL` vendor override jaise stealth tricks use hain.
- Human-like delays, typing, scrolling, mouse moving implement hain.
- Popups aur cookie consents dismiss karne ke helper methods hain.

## 6. User-facing Features
- Multiple bot accounts support via backend
- Proxy configuration per account
- Session persistence via cookies
- Media download support for images, videos, reels, stories, carousels
- Action logging for follow/like/unfollow/download/scrape
- Backend analytics APIs for dashboard use
- Rate limit / health monitoring endpoints

## 7. Repo Limitations / Note
Yeh repo abhi bhi "educational / prototype" level ka system hai:
- Full production-ready error handling aur retry policies may be incomplete
- Backend docs mention some planned endpoints as "work in progress"
- Frontend or Spark jobs are part of architecture but unverified from code inspection
- Instagram policies aur legal compliance abhi bhi check karna zaroori hai

## 8. Company explanation summary
Aap company ko bolein:
- Yeh ek **Instagram automation platform** hai jo Instagram actions ko automate karta hai with backend control.
- `orchestrator/` worker actual session chalata hai, `automation/playwright_engine/` browser se Instagram interact karta hai.
- `backend/` APIs account management, download queue, analytics aur session control provide karte hain.
- `automation/downloader/` media files download karke local storage ya S3 style upload option support karta hai.
- Cookies sync aur session validation implement hai taaki bot accounts zyada ache se reuse ho sake.
- Ye project full-stack architecture show karta hai, aur future me Spark/ML + deployment modules add kiye ja sakte hain.

---

> Note: Yeh repo ka code mainly Python-based automation + Django backend par focused hai. Aapko company me simple se technical presentation ke liye actual file names aur class names mention karni chahiye, jaise `BotWorker`, `InstagramBrowser`, `MediaDownloader`, `InstaApiClient`, aur `CookieSync`.
