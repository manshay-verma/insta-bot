"""
Selenium Adapter

Connects orchestrator with automation/selenium/
Provides backup browser automation when Playwright fails.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any

from .base_adapter import BaseAdapter, AdapterType, TaskType, TaskResult

# Ensure repo root is on sys.path so `automation.*` imports work reliably
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from automation.selenium_engine.driver_manager import DriverManager, BrowserType
    from automation.selenium_engine.navigation import Navigation
    from automation.selenium_engine.auth.login import SeleniumLogin
    from automation.selenium_engine.scraper.profile_scraper import ProfileScraper
except ImportError as e:
    DriverManager = BrowserType = Navigation = SeleniumLogin = ProfileScraper = None
    _selenium_import_error = e

logger = logging.getLogger(__name__)


class SeleniumAdapter(BaseAdapter):
    """
    Adapter for Selenium browser automation.
    
    Wraps:
    - automation/selenium/driver_manager.py (DriverManager)
    - automation/selenium/navigation.py (Navigation)
    - automation/selenium/fallback_handler.py (FallbackHandler)
    
    Supported Tasks:
    - LOGIN, SCRAPE_PROFILE
    
    Usage:
        adapter = SeleniumAdapter(api_client, account_id=1)
        await adapter.initialize()
        result = await adapter.execute(TaskType.SCRAPE_PROFILE, ["instagram"])
        await adapter.cleanup()
    """
    
    adapter_type = AdapterType.SELENIUM
    
    def __init__(self, *args, headless: bool = True, browser: str = "chrome", **kwargs):
        super().__init__(*args, **kwargs)
        self.headless = headless
        self.browser_type = browser
        self.driver_manager = None
        self.driver = None
        self.navigation = None
    
    async def initialize(self) -> bool:
        """Initialize Selenium WebDriver."""
        if DriverManager is None or Navigation is None:
            logger.error(f"Failed to import Selenium modules: {_selenium_import_error}")
            return False
        try:
            # Fetch account for proxy config
            await self.fetch_account()
            proxy = self.get_proxy_config()
            proxy_url = proxy.get("server") if proxy else None
            
            # Determine browser type
            browser_enum = BrowserType.CHROME if self.browser_type == "chrome" else BrowserType.FIREFOX
            
            self.driver_manager = DriverManager(
                browser_type=browser_enum,
                headless=self.headless,
                proxy=proxy_url
            )
            
            self.driver = self.driver_manager.get_persistent_driver()
            self.navigation = Navigation(self.driver)
            
            self._initialized = True
            logger.info(f"Selenium {self.browser_type} initialized")
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import Selenium modules: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {e}")
            return False
    
    async def cleanup(self):
        """Close WebDriver."""
        if self.driver_manager:
            self.driver_manager.close()
            self.driver_manager = None
            self.driver = None
            self.navigation = None
        self._initialized = False
        logger.info("Selenium WebDriver closed")
    
    def get_supported_tasks(self) -> List[TaskType]:
        """Get supported task types."""
        return [
            TaskType.LOGIN,
            TaskType.SCRAPE_PROFILE,
        ]
    
    async def execute(
        self,
        task_type: TaskType,
        targets: List[str],
        **kwargs
    ) -> TaskResult:
        """Execute a Selenium task."""
        if not self._initialized:
            return TaskResult(
                success=False,
                task_type=task_type,
                errors=["Adapter not initialized"]
            )
        
        handlers = {
            TaskType.LOGIN: self._login,
            TaskType.SCRAPE_PROFILE: self._scrape_profiles,
        }
        
        handler = handlers.get(task_type)
        if not handler:
            return TaskResult(
                success=False,
                task_type=task_type,
                errors=[f"Unsupported task: {task_type}"]
            )
        
        # Selenium is synchronous, wrap in executor
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: handler(targets, **kwargs))
    
    # ==================== Task Handlers ====================
    
    def _login(self, targets: List[str], **kwargs) -> TaskResult:
        """Login to Instagram via Selenium."""
        username = self._account_data.get("username")
        
        if SeleniumLogin is None:
            return TaskResult(
                success=False,
                task_type=TaskType.LOGIN,
                errors=[f"Selenium login is unavailable: {_selenium_import_error}"]
            )

        try:
            login_handler = SeleniumLogin(self.driver)
            success = login_handler.login(username, "")  # Use cookies
            
            return TaskResult(
                success=success,
                task_type=TaskType.LOGIN,
                data={"username": username, "method": "selenium"}
            )
        except Exception as e:
            return TaskResult(
                success=False,
                task_type=TaskType.LOGIN,
                errors=[str(e)]
            )
    
    def _scrape_profiles(self, targets: List[str], **kwargs) -> TaskResult:
        """Scrape profiles via Selenium."""
        results = []
        errors = []
        
        if ProfileScraper is None:
            errors.append("ProfileScraper not available")
            return TaskResult(
                success=False,
                task_type=TaskType.SCRAPE_PROFILE,
                data={"profiles": results},
                items_processed=len(results),
                errors=errors
            )

        scraper = ProfileScraper(self.driver)

        for username in targets:
            try:
                profile = scraper.scrape_profile(username)
                if profile:
                    results.append(profile)
                    if self.callback:
                        self.callback.on_scrape_profile(username, True, profile)
            except Exception as e:
                errors.append(f"@{username}: {str(e)}")
                if self.callback:
                    self.callback.on_scrape_profile(username, False, error_message=str(e))

        return TaskResult(
            success=len(results) > 0,
            task_type=TaskType.SCRAPE_PROFILE,
            data={"profiles": results},
            items_processed=len(results),
            errors=errors
        )
    
    # ==================== Fallback Handler ====================
    
    async def trigger_fallback(self, failed_task: TaskType, targets: List[str]) -> TaskResult:
        """
        Called when Playwright fails, try with Selenium as backup.
        
        Usage:
            if playwright_result.success == False:
                result = await selenium_adapter.trigger_fallback(task, targets)
        """
        logger.info(f"Fallback triggered for {failed_task}")
        
        if not self._initialized:
            await self.initialize()
        
        return await self.execute(failed_task, targets)
