# Insta-Bot documentation

Audited documentation lives here. Older roadmaps and plans are in [`legacy/`](legacy/README.md) and should not be treated as the current architecture.

| Document | What it answers |
| --- | --- |
| [architecture/PROJECT_OVERVIEW.md](architecture/PROJECT_OVERVIEW.md) | What the system is, where code lives, and which processes actually run |
| [architecture/ORCHESTRATOR_ARCHITECTURE.md](architecture/ORCHESTRATOR_ARCHITECTURE.md) | How a queued job reaches a browser runner |
| [architecture/AUTOMATION_ARCHITECTURE.md](architecture/AUTOMATION_ARCHITECTURE.md) | Playwright, adapters, sessions, cookies, and modules that are not on the live path |
| [architecture/COMPONENT_INTEGRATION_MATRIX.md](architecture/COMPONENT_INTEGRATION_MATRIX.md) | Whether each expected link is working, partial, broken, or unused |
| [architecture/SPARK_AND_BACKGROUND_JOBS.md](architecture/SPARK_AND_BACKGROUND_JOBS.md) | Celery tasks, reconciliation, and the unwired Spark scripts |
| [audit/REPOSITORY_CLEANUP_REPORT.md](audit/REPOSITORY_CLEANUP_REPORT.md) | What was deleted, what was kept, and why |
| [audit/TEST_SUITE_REVIEW.md](audit/TEST_SUITE_REVIEW.md) | Test classification and removals |
| [audit/DEPENDENCY_REVIEW.md](audit/DEPENDENCY_REVIEW.md) | Requirement files and Compose services |
| [audit/FINAL_REPOSITORY_REVIEW.md](audit/FINAL_REPOSITORY_REVIEW.md) | Health assessment after cleanup |
| [api/API_INVENTORY.md](api/API_INVENTORY.md) | Every mounted HTTP and WebSocket route |
| [api/API_EXECUTION_FLOWS.md](api/API_EXECUTION_FLOWS.md) | What happens after the important requests |
| [api/API_DEPENDENCY_MATRIX.md](api/API_DEPENDENCY_MATRIX.md) | Which APIs touch the database, Celery, the orchestrator, or nothing beyond the view |

Agent navigation notes are in [`.agents/rules/`](../.agents/rules/).
