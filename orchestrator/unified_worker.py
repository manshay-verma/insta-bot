"""
Unified Worker - Multi-Backend Bot Orchestrator

Supports all automation backends:
- Playwright (browser automation)
- Selenium (backup browser)
- Scrapy (bulk scraping)
- Downloader (media downloads)
- Safety (rate limiting)
"""

import asyncio
import logging
from typing import Optional, Dict, List, Any, Union
from dataclasses import dataclass
from enum import Enum

from .api_client import InstaApiClient
from .callbacks import ActionCallback
from .adapters import (
    BaseAdapter,
    AdapterType,
    PlaywrightAdapter,
    SeleniumAdapter,
    ScrapyAdapter,
    DownloaderAdapter,
    SafetyAdapter,
)
from .adapters.base_adapter import TaskType, TaskResult

logger = logging.getLogger(__name__)


@dataclass
class UnifiedResult:
    """Result from unified worker."""
    success: bool
    adapter_type: AdapterType
    task_type: TaskType
    items_processed: int = 0
    errors: List[str] = None
    data: Optional[Dict] = None
    session_id: Optional[int] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class UnifiedWorker:
    """
    Multi-backend bot orchestrator.
    
    Uses adapters to support multiple automation backends:
    - Playwright for browser automation
    - Selenium as backup browser
    - Scrapy for bulk scraping
    - Downloader for media downloads
    - Safety for rate limiting
    
    Usage:
        worker = UnifiedWorker(account_id=1)
        
        # Browser task (Playwright)
        result = await worker.execute(
            adapter_type=AdapterType.PLAYWRIGHT,
            task_type=TaskType.SCRAPE_PROFILE,
            targets=["instagram", "cristiano"]
        )
        
        # Bulk scraping (Scrapy)
        result = await worker.execute(
            adapter_type=AdapterType.SCRAPY,
            task_type=TaskType.SCRAPE_HASHTAG,
            targets=["travel", "photography"],
            max_posts=100
        )
        
        # Download media
        result = await worker.execute(
            adapter_type=AdapterType.DOWNLOADER,
            task_type=TaskType.BULK_DOWNLOAD,
            targets=["url1", "url2"]
        )
    """
    
    def __init__(
        self,
        account_id: int,
        api_client: InstaApiClient = None,
        headless: bool = True
    ):
        self.account_id = account_id
        self.api_client = api_client or InstaApiClient()
        self.headless = headless
        
        self.session_id: Optional[int] = None
        self.callback: Optional[ActionCallback] = None
        self._adapters: Dict[AdapterType, BaseAdapter] = {}
    
    def _create_adapter(self, adapter_type: AdapterType) -> BaseAdapter:
        """Create an adapter instance."""
        adapter_classes = {
            AdapterType.PLAYWRIGHT: PlaywrightAdapter,
            AdapterType.SELENIUM: SeleniumAdapter,
            AdapterType.SCRAPY: ScrapyAdapter,
            AdapterType.DOWNLOADER: DownloaderAdapter,
            AdapterType.SAFETY: SafetyAdapter,
        }
        
        cls = adapter_classes.get(adapter_type)
        if not cls:
            raise ValueError(f"Unknown adapter type: {adapter_type}")
        
        return cls(
            api_client=self.api_client,
            account_id=self.account_id,
            callback=self.callback
        )
    
    async def get_adapter(self, adapter_type: AdapterType) -> BaseAdapter:
        """Get or create an adapter, initializing if needed."""
        if adapter_type not in self._adapters:
            adapter = self._create_adapter(adapter_type)
            await adapter.initialize()
            self._adapters[adapter_type] = adapter
        
        return self._adapters[adapter_type]
    
    async def start_session(self) -> bool:
        """Start a backend session."""
        response = self.api_client.start_session(self.account_id)
        if response.success:
            self.session_id = response.data.get("session_id")
            self.callback = ActionCallback(
                api_client=self.api_client,
                account_id=self.account_id,
                session_id=self.session_id
            )
            logger.info(f"Started session: {self.session_id}")
            return True
        return False
    
    async def stop_session(self):
        """Stop the backend session."""
        if self.session_id:
            self.api_client.stop_session(self.account_id)
            logger.info(f"Stopped session: {self.session_id}")
    
    async def execute(
        self,
        adapter_type: Union[AdapterType, str],
        task_type: Union[TaskType, str],
        targets: List[str],
        **kwargs
    ) -> UnifiedResult:
        """
        Execute a task using specified adapter.
        
        Args:
            adapter_type: Which automation backend to use
            task_type: Type of task to execute
            targets: List of usernames, URLs, hashtags, etc.
            **kwargs: Task-specific parameters
            
        Returns:
            UnifiedResult with execution details
        """
        # Convert strings to enums
        if isinstance(adapter_type, str):
            adapter_type = AdapterType(adapter_type)
        if isinstance(task_type, str):
            task_type = TaskType(task_type)
        
        try:
            # Get/create adapter
            adapter = await self.get_adapter(adapter_type)
            
            # Check if task is supported
            if not adapter.supports_task(task_type):
                return UnifiedResult(
                    success=False,
                    adapter_type=adapter_type,
                    task_type=task_type,
                    errors=[f"{adapter_type.value} doesn't support {task_type.value}"]
                )
            
            # Execute task
            result = await adapter.execute(task_type, targets, **kwargs)
            
            return UnifiedResult(
                success=result.success,
                adapter_type=adapter_type,
                task_type=task_type,
                items_processed=result.items_processed,
                errors=result.errors,
                data=result.data,
                session_id=self.session_id
            )
            
        except Exception as e:
            logger.exception(f"Execution failed: {e}")
            return UnifiedResult(
                success=False,
                adapter_type=adapter_type,
                task_type=task_type,
                errors=[str(e)]
            )
    
    async def execute_with_fallback(
        self,
        task_type: TaskType,
        targets: List[str],
        primary: AdapterType = AdapterType.PLAYWRIGHT,
        fallback: AdapterType = AdapterType.SELENIUM,
        **kwargs
    ) -> UnifiedResult:
        """
        Execute with fallback to another adapter if primary fails.
        
        Useful for browser tasks where Selenium can backup Playwright.
        """
        # Try primary
        result = await self.execute(primary, task_type, targets, **kwargs)
        
        if result.success:
            return result
        
        # Fallback
        logger.info(f"Primary {primary.value} failed, trying {fallback.value}")
        return await self.execute(fallback, task_type, targets, **kwargs)
    
    async def execute_with_safety(
        self,
        adapter_type: AdapterType,
        task_type: TaskType,
        targets: List[str],
        **kwargs
    ) -> UnifiedResult:
        """
        Execute task with safety checks (rate limiting, delays).
        """
        safety = await self.get_adapter(AdapterType.SAFETY)
        
        # Check rate limit
        rate_check = await safety.execute(
            TaskType.CHECK_RATE_LIMIT,
            [task_type.value]
        )
        
        if rate_check.data and not rate_check.data.get("allowed", True):
            return UnifiedResult(
                success=False,
                adapter_type=adapter_type,
                task_type=task_type,
                errors=["Rate limit exceeded"]
            )
        
        # Get delay
        delay_result = await safety.execute(TaskType.GET_DELAY, [task_type.value])
        delay = delay_result.data.get("delay", 2.0) if delay_result.data else 2.0
        
        results = []
        for target in targets:
            # Execute single action
            result = await self.execute(adapter_type, task_type, [target], **kwargs)
            results.append(result)
            
            # Apply delay between actions
            await asyncio.sleep(delay)
        
        # Aggregate results
        success_count = sum(1 for r in results if r.success)
        all_errors = [e for r in results for e in r.errors]
        
        return UnifiedResult(
            success=success_count > 0,
            adapter_type=adapter_type,
            task_type=task_type,
            items_processed=success_count,
            errors=all_errors,
            session_id=self.session_id
        )
    
    async def cleanup(self):
        """Cleanup all adapters."""
        for adapter in self._adapters.values():
            await adapter.cleanup()
        self._adapters.clear()
        logger.info("All adapters cleaned up")
    
    async def __aenter__(self):
        await self.start_session()
        return self
    
    async def __aexit__(self, *args):
        await self.cleanup()
        await self.stop_session()
