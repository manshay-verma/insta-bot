# InstaBot Detailed Explanation (2 Years Experience Level)

## 1. Introduction
Yeh document ek medium-level technical explanation hai jise aap company me present kar sakte ho. Target audience ho sakti hai product manager, operations, ya technical lead jinhone ek moderate technical background hai.

## 2. Project Goal
Project ka main goal hai:
- Instagram se structured data aur media collect karna
- Multiple bot accounts se safe automation karna
- Backend APIs aur analytics provide karna
- Downloaded content ko manage karna
- Future-ready cloud aur big-data integration support karna

## 3. Business Use Cases
1. **Market research**: Competitor profiles, trending hashtags, post performance data collect karna.
2. **Content aggregation**: Reels, stories, image downloads ek jagah store karna.
3. **Automation campaigns**: Follow, like, comment flows automate karna for multiple accounts.
4. **Analytics and reporting**: Bot health, action counts, download history track karna.
5. **Safety-first operations**: Rate limiting aur proxy usage se account risk kam karna.

## 4. High-Level Architecture

### 4.1 System components
- `frontend/`: React + Vite dashboard for monitoring and control.
- `backend/`: Django REST API server for all business logic.
- `automation/`: Core bot engines, scraper logic, media downloader, auto-safety.
- `node_service/`: Real-time service aur background workers.
- `orchestrator/`: Task coordination, callbacks, unified worker handling.
- `spark_jobs/`: Big data processing, batch/streaming aur ML experiments.
- `infradocker/`, `infrascripts/`, `infraterraform/`: Deployment and infra automation.

### 4.2 Interaction flow
1. User/dashboard request backend.
2. Backend validates aur task create karta hai.
3. Orchestrator/worker request automation engine ko forward karta hai.
4. Automation engine Instagram visit karke data scrape ya action execute karta hai.
5. Results database / storage me save hoti hain.
6. Frontend ko realtime updates milti hain via WebSocket/Node service.

## 5. Detailed Module Flow

### 5.1 Automation Layer
- `automation/playwright_engine/`: Primary browser automation tool.
- `automation/selenium/`: supplementary browser automation support.
- `automation/downloader/media_downloader.py`: media URL resolve, download, retry logic.
- `automation/multi_account_manager.py`: multiple accounts handle karna, session reuse, proxy binding.
- `automation/safety/`: rate limits, ban detection, behavior policies.

#### Kaise kaam karta hai?
- Pehle account select hota hai.
- Browser session launch hota hai with Playwright.
- Instagram URL par navigate kia jata hai.
- Required data fetch ki jati hai (profile, post, story, reel).
- Agar media download request hai to `media_downloader` use hota hai.
- Action logs aur errors backend ko send hoti hain.

### 5.2 Backend Layer
- `backend/manage.py`: Django project entrypoint.
- `backend/account/`: Instagram account aur proxy management.
- `backend/analytics/`: action metrics, performance summaries, dashboard APIs.
- `backend/downloads/`: download queue, history, status.
- `backend/cookies/`: session cookie storage and refresh.
- `backend/services/`: shared service logic, utilities.

#### Key APIs
- `POST /api/v1/accounts/` : naya bot account add.
- `GET /api/v1/accounts/` : bot list.
- `POST /api/v1/bots/control/` : start/stop bot.
- `GET /api/v1/bots/status/` : current running bots.
- `POST /api/v1/downloads/bulk/` : download queue add.
- `GET /api/v1/history/` : past downloads.
- `GET /api/v1/analytics/dashboard/` : summary stats.

### 5.3 Orchestrator & Node Service
- `orchestrator/bot_worker.py`: bot execution logic.
- `orchestrator/unified_worker.py`: tasks ko unify karta hai across modules.
- `orchestrator/callbacks.py`: task completion callbacks.
- `node_service/src/`: WebSocket aur realtime message delivery.

### 5.4 Big Data & Analytics
- `spark_jobs/spark_app.py`: Spark job entrypoint.
- `spark_jobs/batch/`, `spark_jobs/streaming/`, `spark_jobs/ml/`: ETL aur model code.
- Yeh layer future-ready hai for large dataset processing and recommendation engine.

## 6. Safety and Reliability

### 6.1 Account safety
- Multiple account support with `automation/multi_account_manager.py`.
- Each account alag proxy use kar sakta hai.
- Session cookies reuse karke Instagram login retry kam hoti hai.

### 6.2 Rate limiting
- `automation/safety/` module actions ko throttle karta hai.
- Follow/like/comment counts limit hote hain.
- `health` and `rate-limits` APIs se company real-time risk dekh sakti hai.

### 6.3 Error handling
- Retry logic `media_downloader` me implement ho sakta hai.
- Task queue aur background workers failures ko handle karte hain.
- Logging aur analytics se failure reasons trace ho sakte hain.

## 7. Data Flow Example

### Example: Reels download workflow
1. Frontend: user 50 reel URLs `POST /downloads/bulk/` send karta hai.
2. Backend: queue create hoti hai, download tasks generate hoti hain.
3. Orchestrator: worker tasks ko pick karta hai.
4. Playwright engine reel page open karta hai.
5. `media_downloader.py` direct media URL resolve karta hai.
6. File local storage ya S3 me save hoti hai.
7. Backend download history update hoti hai.
8. Frontend progress `GET /queue/` / WebSocket se receive karta hai.

## 8. Technology Stack
- **Language**: Python
- **Backend**: Django
- **Automation**: Playwright, Selenium
- **Frontend**: React + Vite
- **Real-time**: Node.js WebSocket service
- **Data**: SQLite / SQL, plus NoSQL options possible
- **Big Data**: Apache Spark
- **Deployment**: Docker, Terraform, AWS-ready

## 9. Why yeh project important hai
- **Modular design**: alag layers alag functionalities clearly define karti hain.
- **Production-ready focus**: logging, task orchestration, rate limiting, session management.
- **Scalable future**: Spark aur infra modules add karte hain big-data capability.
- **Business value**: marketing intelligence, content aggregation aur automation operations simplify karta hai.

## 10. Present karne ka tarika
1. Start with problem statement: "Instagram data automation aur analytics need hai." 
2. Fir architecture dikhao: frontend → API → orchestrator → automation → Instagram.
3. Explain key modules: accounts, downloads, safety, analytics.
4. Use real folder names (`automation/`, `backend/`, `orchestrator/`) to show familiarity.
5. End with business value aur next steps: AWS deployment, recommendation engine, scaling.

---

> Note: Project educational purpose ke liye bana hai. Real Instagram automation use karne se pehle policy aur legal compliance check karna zaroori hai.
