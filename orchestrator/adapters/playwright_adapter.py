"""
Playwright Adapter

Connects orchestrator with automation/playwright/browser_manager.py
Provides browser automation for Instagram actions.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any

from .base_adapter import BaseAdapter, AdapterType, TaskType, TaskResult

# Add automation to path
automation_path = Path(__file__).parent.parent.parent / "automation"
sys.path.insert(0, str(automation_path))

logger = logging.getLogger(__name__)


class PlaywrightAdapter(BaseAdapter):
    """
    Adapter for Playwright browser automation.
    
    Wraps InstagramBrowser from automation/playwright/browser_manager.py
    
    Supported Tasks:
    - LOGIN, SCRAPE_PROFILE, SCRAPE_POSTS
    - LIKE_POSTS, UNLIKE_POSTS
    - FOLLOW_USERS, UNFOLLOW_USERS
    - VIEW_STORIES, COMMENT
    
    Usage:
        adapter = PlaywrightAdapter(api_client, account_id=1, callback=cb)
        await adapter.initialize()
        result = await adapter.execute(TaskType.SCRAPE_PROFILE, ["instagram"])
        await adapter.cleanup()
    """
    
    adapter_type = AdapterType.PLAYWRIGHT
    
    def __init__(self, *args, headless: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.headless = headless
        self.browser = None
        self._logged_in = False
    
    async def initialize(self) -> bool:
        """Initialize Playwright browser."""
        try:
            from playwright.browser_manager import InstagramBrowser
            
            # Fetch account for proxy config
            await self.fetch_account()
            proxy = self.get_proxy_config()
            
            self.browser = InstagramBrowser(
                headless=self.headless,
                proxy=proxy
            )
            
            await self.browser.start()
            self._initialized = True
            logger.info("Playwright browser initialized")
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import Playwright: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            return False
    
    async def cleanup(self):
        """Close browser."""
        if self.browser:
            try:
                await self.browser.__aexit__(None, None, None)
            except:
                pass
            self.browser = None
        self._initialized = False
        self._logged_in = False
        logger.info("Playwright browser closed")
    
    def get_supported_tasks(self) -> List[TaskType]:
        """Get supported task types."""
        return [
            TaskType.LOGIN,
            TaskType.SCRAPE_PROFILE,
            TaskType.SCRAPE_POSTS,
            TaskType.LIKE_POSTS,
            TaskType.UNLIKE_POSTS,
            TaskType.FOLLOW_USERS,
            TaskType.UNFOLLOW_USERS,
            TaskType.VIEW_STORIES,
            TaskType.COMMENT,
        ]
    
    async def execute(
        self,
        task_type: TaskType,
        targets: List[str],
        **kwargs
    ) -> TaskResult:
        """Execute a Playwright task."""
        if not self._initialized:
            return TaskResult(
                success=False,
                task_type=task_type,
                errors=["Adapter not initialized"]
            )
        
        # Dispatch to specific handler
        handlers = {
            TaskType.LOGIN: self._login,
            TaskType.SCRAPE_PROFILE: self._scrape_profiles,
            TaskType.SCRAPE_POSTS: self._scrape_posts,
            TaskType.LIKE_POSTS: self._like_posts,
            TaskType.UNLIKE_POSTS: self._unlike_posts,
            TaskType.FOLLOW_USERS: self._follow_users,
            TaskType.UNFOLLOW_USERS: self._unfollow_users,
            TaskType.VIEW_STORIES: self._view_stories,
            TaskType.COMMENT: self._comment,
        }
        
        handler = handlers.get(task_type)
        if not handler:
            return TaskResult(
                success=False,
                task_type=task_type,
                errors=[f"Unsupported task: {task_type}"]
            )
        
        return await handler(targets, **kwargs)
    
    # ==================== Task Handlers ====================
    
    async def _login(self, targets: List[str], **kwargs) -> TaskResult:
        """Login to Instagram."""
        from orchestrator.cookie_sync import CookieSync
        
        username = self._account_data.get("username")
        cookie_sync = CookieSync(self.api_client, self.account_id)
        
        # Try cookie login first
        cookies = cookie_sync.load_from_backend()
        cookie_path = None
        
        if cookies:
            cookie_path = str(cookie_sync.cookie_file_path)
            cookie_sync.export_to_file(cookies)
        
        try:
            await self.browser.login(
                username=username,
                password="",  # Uses cookies
                cookie_path=cookie_path
            )
            
            if await self.browser.is_session_valid():
                self._logged_in = True
                return TaskResult(
                    success=True,
                    task_type=TaskType.LOGIN,
                    data={"username": username, "method": "cookies"}
                )
            else:
                return TaskResult(
                    success=False,
                    task_type=TaskType.LOGIN,
                    errors=["Session invalid after login"]
                )
        except Exception as e:
            return TaskResult(
                success=False,
                task_type=TaskType.LOGIN,
                errors=[str(e)]
            )
    
    async def _scrape_profiles(self, targets: List[str], **kwargs) -> TaskResult:
        """Scrape profile info for usernames."""
        results = []
        errors = []
        
        for username in targets:
            try:
                profile = await self.browser.extract_profile_info(username)
                if profile:
                    results.append(profile)
                    if self.callback:
                        self.callback.on_scrape_profile(username, True, profile)
                else:
                    errors.append(f"No data for @{username}")
                    if self.callback:
                        self.callback.on_scrape_profile(username, False)
            except Exception as e:
                errors.append(f"@{username}: {str(e)}")
                if self.callback:
                    self.callback.on_scrape_profile(username, False, error_message=str(e))
        
        return TaskResult(
            success=len(errors) == 0,
            task_type=TaskType.SCRAPE_PROFILE,
            data={"profiles": results},
            items_processed=len(results),
            errors=errors
        )
    
    async def _scrape_posts(self, targets: List[str], **kwargs) -> TaskResult:
        """Scrape posts from profiles."""
        max_posts = kwargs.get("max_posts", 10)
        results = []
        errors = []
        
        for username in targets:
            try:
                await self.browser.visit_profile(username)
                # Note: extract_posts method would need to be implemented
                # For now return placeholder
                results.append({"username": username, "posts": []})
                if self.callback:
                    self.callback.on_scrape_posts(username, 0, True)
            except Exception as e:
                errors.append(f"@{username}: {str(e)}")
        
        return TaskResult(
            success=len(errors) == 0,
            task_type=TaskType.SCRAPE_POSTS,
            data={"posts": results},
            items_processed=len(results),
            errors=errors
        )
    
    async def _like_posts(self, targets: List[str], **kwargs) -> TaskResult:
        """Like posts by URL."""
        success_count = 0
        errors = []
        
        for url in targets:
            try:
                result = await self.browser.like_post(url)
                if result:
                    success_count += 1
                    if self.callback:
                        self.callback.on_like(url, True)
                else:
                    errors.append(f"Failed to like: {url}")
                    if self.callback:
                        self.callback.on_like(url, False)
            except Exception as e:
                errors.append(str(e))
                if self.callback:
                    self.callback.on_like(url, False, error_message=str(e))
        
        return TaskResult(
            success=success_count > 0,
            task_type=TaskType.LIKE_POSTS,
            items_processed=success_count,
            errors=errors
        )
    
    async def _unlike_posts(self, targets: List[str], **kwargs) -> TaskResult:
        """Unlike posts by URL."""
        success_count = 0
        errors = []
        
        for url in targets:
            try:
                result = await self.browser.unlike_post(url)
                if result:
                    success_count += 1
                    if self.callback:
                        self.callback.on_unlike(url, True)
            except Exception as e:
                errors.append(str(e))
        
        return TaskResult(
            success=success_count > 0,
            task_type=TaskType.UNLIKE_POSTS,
            items_processed=success_count,
            errors=errors
        )
    
    async def _follow_users(self, targets: List[str], **kwargs) -> TaskResult:
        """Follow users by username."""
        success_count = 0
        errors = []
        
        for username in targets:
            try:
                result = await self.browser.follow_user(username)
                if result:
                    success_count += 1
                    if self.callback:
                        self.callback.on_follow(username, True)
                else:
                    if self.callback:
                        self.callback.on_follow(username, False)
            except Exception as e:
                errors.append(f"@{username}: {str(e)}")
                if self.callback:
                    self.callback.on_follow(username, False, error_message=str(e))
        
        return TaskResult(
            success=success_count > 0,
            task_type=TaskType.FOLLOW_USERS,
            items_processed=success_count,
            errors=errors
        )
    
    async def _unfollow_users(self, targets: List[str], **kwargs) -> TaskResult:
        """Unfollow users by username."""
        success_count = 0
        errors = []
        
        for username in targets:
            try:
                result = await self.browser.unfollow_user(username)
                if result:
                    success_count += 1
                    if self.callback:
                        self.callback.on_unfollow(username, True)
            except Exception as e:
                errors.append(f"@{username}: {str(e)}")
        
        return TaskResult(
            success=success_count > 0,
            task_type=TaskType.UNFOLLOW_USERS,
            items_processed=success_count,
            errors=errors
        )
    
    async def _view_stories(self, targets: List[str], **kwargs) -> TaskResult:
        """View stories by username."""
        success_count = 0
        errors = []
        
        for username in targets:
            try:
                stories = await self.browser.view_stories(username)
                count = len(stories) if stories else 0
                success_count += 1
                if self.callback:
                    self.callback.on_story_view(username, True, count)
            except Exception as e:
                errors.append(f"@{username}: {str(e)}")
                if self.callback:
                    self.callback.on_story_view(username, False, error_message=str(e))
        
        return TaskResult(
            success=success_count > 0,
            task_type=TaskType.VIEW_STORIES,
            items_processed=success_count,
            errors=errors
        )
    
    async def _comment(self, targets: List[str], **kwargs) -> TaskResult:
        """Comment on posts."""
        comment_text = kwargs.get("comment_text", "")
        success_count = 0
        errors = []
        
        for url in targets:
            try:
                result = await self.browser.comment_on_post(url, comment_text)
                if result:
                    success_count += 1
                    if self.callback:
                        self.callback.on_comment(url, comment_text, True)
            except Exception as e:
                errors.append(str(e))
        
        return TaskResult(
            success=success_count > 0,
            task_type=TaskType.COMMENT,
            items_processed=success_count,
            errors=errors
        )
    
    # ==================== Utility Methods ====================
    
    async def sync_cookies(self) -> bool:
        """Sync cookies back to backend."""
        if not self.browser:
            return False
        
        try:
            from orchestrator.cookie_sync import CookieSync
            
            session_info = await self.browser.get_session_info()
            cookies = session_info.get("cookies", [])
            
            if cookies:
                cookie_sync = CookieSync(self.api_client, self.account_id)
                return cookie_sync.save_to_backend(cookies)
            return False
        except Exception as e:
            logger.error(f"Failed to sync cookies: {e}")
            return False
