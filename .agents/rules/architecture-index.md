---
trigger: always_on
---

# Where the truth lives

Before changing Insta-Bot behavior, read the audited docs instead of `docs/legacy/`.

- Index: `docs/README.md`
- System map: `docs/architecture/PROJECT_OVERVIEW.md`
- Routes: `docs/api/API_INVENTORY.md`
- What happens after a request: `docs/api/API_EXECUTION_FLOWS.md`
- Which routes touch which systems: `docs/api/API_DEPENDENCY_MATRIX.md`
- Worker and runner: `docs/architecture/ORCHESTRATOR_ARCHITECTURE.md`
- Browser and unused engines: `docs/architecture/AUTOMATION_ARCHITECTURE.md`
- Link status (WORKING / PARTIAL / BROKEN / UNUSED): `docs/architecture/COMPONENT_INTEGRATION_MATRIX.md`
- Celery and Spark: `docs/architecture/SPARK_AND_BACKGROUND_JOBS.md`

`docs/legacy/` is historical. Do not treat Spark, Selenium, Scrapy, safety limits, WebSocket job events, or the download queue as wired unless the matrix says WORKING. Those trees were kept on purpose. The cleanup record is `docs/audit/REPOSITORY_CLEANUP_REPORT.md`.

Do not invent a service layer for dashboard routes. Most views write the ORM directly. The automation service is `backend/api/job_service.py`.
