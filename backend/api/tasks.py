import asyncio
import logging

from celery import shared_task

logger = logging.getLogger(__name__)

def _ensure_windows_proactor_loop_policy():
    """
    Playwright spawns a driver process via asyncio subprocess APIs.
    On Windows, subprocess support requires the Proactor event loop.
    """
    import sys
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass


@shared_task(bind=True)
def execute_bot_task(self, account_id: int, action: str, targets: list[str], options: dict | None = None):
    """
    Run a bot action in the background (Celery).

    This mirrors the sync execution path used by `BotExecuteView`, but executes inside a worker.
    """
    options = options or {}

    try:
        from orchestrator import UnifiedWorker, AdapterType, TaskType
    except Exception as e:  # pragma: no cover
        logger.exception("Orchestrator import failed in Celery task.")
        return {
            "success": False,
            "items_processed": 0,
            "errors": [f"Orchestrator not available: {e}"],
        }

    action_map = {
        "like": TaskType.LIKE_POSTS,
        "follow": TaskType.FOLLOW_USERS,
        "unfollow": TaskType.UNFOLLOW_USERS,
        "scrape_profile": TaskType.SCRAPE_PROFILE,
        "view_stories": TaskType.VIEW_STORIES,
        "download": TaskType.BULK_DOWNLOAD,
        "comment": TaskType.COMMENT,
    }

    task_type = action_map.get(action)
    if not task_type:
        return {"success": False, "items_processed": 0, "errors": [f"Unknown action: {action}"]}

    adapter_type = AdapterType.PLAYWRIGHT
    if action == "download":
        adapter_type = AdapterType.DOWNLOADER

    async def _run():
        worker = UnifiedWorker(account_id=account_id)
        try:
            await worker.start_session()
            result = await worker.execute(adapter_type, task_type, targets, **options)
            return {
                "success": result.success,
                "items_processed": result.items_processed,
                "errors": result.errors,
                "processed": targets[: result.items_processed],
            }
        finally:
            try:
                await worker.cleanup()
            finally:
                await worker.stop_session()

    try:
        _ensure_windows_proactor_loop_policy()
        return asyncio.run(_run())
    except Exception as e:  # pragma: no cover
        logger.exception("Celery bot execution failed.")
        return {"success": False, "items_processed": 0, "errors": [str(e)]}

