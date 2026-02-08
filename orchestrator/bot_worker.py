"""
Bot Worker - Main Orchestrator

Orchestrates complete bot session lifecycle:
1. Fetch account credentials from backend
2. Initialize browser with proxy
3. Login using cookies or credentials
4. Execute automation tasks
5. Log all actions via callbacks
6. Sync cookies back to backend
7. End session properly
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

# Add automation module to path
automation_path = Path(__file__).parent.parent / "automation"
sys.path.insert(0, str(automation_path))

from .api_client import InstaApiClient, AccountStatus
from .callbacks import ActionCallback
from .cookie_sync import CookieSync


logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Supported automation task types."""
    SCRAPE_PROFILE = "scrape_profile"
    SCRAPE_POSTS = "scrape_posts"
    LIKE_POSTS = "like_posts"
    FOLLOW_USERS = "follow_users"
    UNFOLLOW_USERS = "unfollow_users"
    VIEW_STORIES = "view_stories"
    DOWNLOAD_MEDIA = "download_media"


@dataclass
class TaskConfig:
    """Configuration for automation task."""
    task_type: TaskType
    targets: List[str]  # Usernames or URLs
    max_actions: int = 10
    delay_min: float = 2.0
    delay_max: float = 5.0
    metadata: Optional[Dict] = None


@dataclass
class WorkerResult:
    """Result of a worker run."""
    success: bool
    session_id: Optional[int] = None
    actions_count: int = 0
    errors_count: int = 0
    error_message: Optional[str] = None
    summary: Optional[Dict] = None


class BotWorker:
    """
    Orchestrates a complete bot session.
    
    Bridges automation scripts with backend by:
    - Fetching credentials and proxy from backend
    - Managing browser sessions
    - Logging actions back to backend
    - Syncing cookies for session persistence
    
    Usage:
        worker = BotWorker(account_id=1)
        
        # Run a task
        result = await worker.run(TaskConfig(
            task_type=TaskType.SCRAPE_PROFILE,
            targets=["instagram", "cristiano"]
        ))
        
        print(result.summary)
    """
    
    def __init__(
        self,
        account_id: int,
        api_client: InstaApiClient = None,
        headless: bool = True,
        auto_cookie_sync: bool = True
    ):
        """
        Initialize bot worker.
        
        Args:
            account_id: Backend account ID
            api_client: Optional API client (creates new if None)
            headless: Run browser in headless mode
            auto_cookie_sync: Automatically sync cookies after session
        """
        self.account_id = account_id
        self.api_client = api_client or InstaApiClient()
        self.headless = headless
        self.auto_cookie_sync = auto_cookie_sync
        
        # Will be set during run
        self.session_id: Optional[int] = None
        self.account_data: Optional[Dict] = None
        self.callback: Optional[ActionCallback] = None
        self.cookie_sync: Optional[CookieSync] = None
        self.browser = None
    
    async def _fetch_account(self) -> bool:
        """Fetch account data from backend."""
        response = self.api_client.get_account(self.account_id)
        
        if not response.success:
            logger.error(f"Failed to fetch account: {response.error}")
            return False
        
        self.account_data = response.data
        logger.info(f"Loaded account: @{self.account_data.get('username')}")
        return True
    
    async def _start_session(self) -> bool:
        """Start a new session in backend."""
        response = self.api_client.start_session(self.account_id)
        
        if not response.success:
            logger.error(f"Failed to start session: {response.error}")
            return False
        
        self.session_id = response.data.get("session_id")
        logger.info(f"Started session: {self.session_id}")
        return True
    
    async def _stop_session(self):
        """Stop the current session."""
        if self.session_id:
            self.api_client.stop_session(self.account_id)
            logger.info(f"Stopped session: {self.session_id}")
    
    def _get_proxy_config(self) -> Optional[Dict]:
        """Build proxy config from account data."""
        if not self.account_data:
            return None
        
        proxy_data = self.account_data.get("proxy")
        if not proxy_data:
            return None
        
        proxy_config = {
            "server": f"{proxy_data['protocol']}://{proxy_data['host']}:{proxy_data['port']}"
        }
        
        if proxy_data.get("username") and proxy_data.get("password"):
            proxy_config["username"] = proxy_data["username"]
            proxy_config["password"] = proxy_data["password"]
        
        return proxy_config
    
    async def _init_browser(self) -> bool:
        """Initialize browser with automation module."""
        try:
            from playwright.browser_manager import InstagramBrowser
            
            proxy = self._get_proxy_config()
            self.browser = InstagramBrowser(
                headless=self.headless,
                proxy=proxy
            )
            
            await self.browser.start()
            logger.info("Browser initialized")
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import automation module: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            return False
    
    async def _login(self) -> bool:
        """Login to Instagram using cookies or credentials."""
        if not self.browser or not self.account_data:
            return False
        
        username = self.account_data.get("username")
        
        # Initialize cookie sync
        self.cookie_sync = CookieSync(self.api_client, self.account_id)
        
        # Try loading cookies from backend
        cookies = self.cookie_sync.load_from_backend()
        
        if cookies:
            # Export to file for browser
            cookie_path = str(self.cookie_sync.cookie_file_path)
            self.cookie_sync.export_to_file(cookies)
            
            try:
                await self.browser.login(
                    username=username,
                    password="",  # Not needed with cookies
                    cookie_path=cookie_path
                )
                
                if await self.browser.is_session_valid():
                    logger.info(f"Logged in via cookies: @{username}")
                    return True
                    
            except Exception as e:
                logger.warning(f"Cookie login failed: {e}")
        
        # Fallback to password login
        # Note: In production, decrypt password from account_data["password_encrypted"]
        logger.warning("Cookie login failed, manual password login required")
        return False
    
    async def _sync_cookies(self):
        """Sync browser cookies back to backend."""
        if not self.browser or not self.cookie_sync:
            return
        
        try:
            # Get session info which includes cookies
            session_info = await self.browser.get_session_info()
            cookies = session_info.get("cookies", [])
            
            if cookies:
                self.cookie_sync.full_sync(cookies)
                logger.info(f"Synced {len(cookies)} cookies")
                
        except Exception as e:
            logger.error(f"Failed to sync cookies: {e}")
    
    async def _execute_task(self, config: TaskConfig) -> bool:
        """Execute the automation task."""
        if not self.browser or not self.callback:
            return False
        
        logger.info(f"Executing task: {config.task_type.value} on {len(config.targets)} targets")
        
        try:
            for target in config.targets[:config.max_actions]:
                # Add some delay between actions
                import random
                delay = random.uniform(config.delay_min, config.delay_max)
                await asyncio.sleep(delay)
                
                if config.task_type == TaskType.SCRAPE_PROFILE:
                    await self._scrape_profile(target)
                    
                elif config.task_type == TaskType.LIKE_POSTS:
                    await self._like_post(target)
                    
                elif config.task_type == TaskType.FOLLOW_USERS:
                    await self._follow_user(target)
                    
                elif config.task_type == TaskType.VIEW_STORIES:
                    await self._view_stories(target)
                    
                # Add more task types as needed
            
            return True
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return False
    
    async def _scrape_profile(self, username: str):
        """Scrape a user profile."""
        try:
            profile_data = await self.browser.extract_profile_info(username)
            
            if profile_data:
                self.callback.on_scrape_profile(
                    target_username=username,
                    success=True,
                    profile_data=profile_data
                )
            else:
                self.callback.on_scrape_profile(
                    target_username=username,
                    success=False,
                    error_message="No profile data returned"
                )
                
        except Exception as e:
            self.callback.on_scrape_profile(
                target_username=username,
                success=False,
                error_message=str(e)
            )
    
    async def _like_post(self, post_url: str):
        """Like a post."""
        try:
            success = await self.browser.like_post(post_url)
            self.callback.on_like(
                target_url=post_url,
                success=success
            )
        except Exception as e:
            self.callback.on_like(
                target_url=post_url,
                success=False,
                error_message=str(e)
            )
    
    async def _follow_user(self, username: str):
        """Follow a user."""
        try:
            success = await self.browser.follow_user(username)
            self.callback.on_follow(
                target_username=username,
                success=success
            )
        except Exception as e:
            self.callback.on_follow(
                target_username=username,
                success=False,
                error_message=str(e)
            )
    
    async def _view_stories(self, username: str):
        """View user stories."""
        try:
            stories = await self.browser.view_stories(username)
            self.callback.on_story_view(
                target_username=username,
                success=True,
                stories_count=len(stories) if stories else 0
            )
        except Exception as e:
            self.callback.on_story_view(
                target_username=username,
                success=False,
                error_message=str(e)
            )
    
    async def _cleanup(self):
        """Clean up resources."""
        if self.browser:
            try:
                await self.browser.__aexit__(None, None, None)
            except:
                pass
    
    async def run(self, config: TaskConfig) -> WorkerResult:
        """
        Run a complete bot session.
        
        Args:
            config: Task configuration
            
        Returns:
            WorkerResult with session summary
        """
        logger.info(f"Starting bot worker for account {self.account_id}")
        
        try:
            # Step 1: Fetch account from backend
            if not await self._fetch_account():
                return WorkerResult(
                    success=False,
                    error_message="Failed to fetch account from backend"
                )
            
            # Check account status
            if self.account_data.get("status") != "active":
                return WorkerResult(
                    success=False,
                    error_message=f"Account is not active: {self.account_data.get('status')}"
                )
            
            # Step 2: Start session
            if not await self._start_session():
                return WorkerResult(
                    success=False,
                    error_message="Failed to start session"
                )
            
            # Step 3: Initialize callback
            self.callback = ActionCallback(
                api_client=self.api_client,
                account_id=self.account_id,
                session_id=self.session_id
            )
            
            # Step 4: Initialize browser
            if not await self._init_browser():
                await self._stop_session()
                return WorkerResult(
                    success=False,
                    session_id=self.session_id,
                    error_message="Failed to initialize browser"
                )
            
            # Step 5: Login
            if not await self._login():
                await self._cleanup()
                await self._stop_session()
                return WorkerResult(
                    success=False,
                    session_id=self.session_id,
                    error_message="Failed to login"
                )
            
            # Step 6: Execute task
            task_success = await self._execute_task(config)
            
            # Step 7: Sync cookies
            if self.auto_cookie_sync:
                await self._sync_cookies()
            
            # Step 8: Get summary
            summary = self.callback.get_summary()
            
            # Step 9: Cleanup
            await self._cleanup()
            await self._stop_session()
            
            return WorkerResult(
                success=task_success,
                session_id=self.session_id,
                actions_count=summary["success_count"],
                errors_count=summary["error_count"],
                summary=summary
            )
            
        except Exception as e:
            logger.exception(f"Worker failed: {e}")
            await self._cleanup()
            await self._stop_session()
            
            return WorkerResult(
                success=False,
                session_id=self.session_id,
                error_message=str(e)
            )
    
    async def run_simple(
        self,
        task_type: TaskType,
        targets: List[str],
        max_actions: int = 10
    ) -> WorkerResult:
        """
        Convenience method for simple task execution.
        
        Args:
            task_type: Type of task to run
            targets: List of usernames or URLs
            max_actions: Maximum actions to perform
            
        Returns:
            WorkerResult
        """
        config = TaskConfig(
            task_type=task_type,
            targets=targets,
            max_actions=max_actions
        )
        return await self.run(config)


# ==================== CLI Entry Point ====================

async def main():
    """CLI entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Bot Worker CLI")
    parser.add_argument("--account", "-a", type=int, required=True, help="Account ID")
    parser.add_argument("--task", "-t", required=True, choices=[t.value for t in TaskType])
    parser.add_argument("--targets", "-u", nargs="+", required=True, help="Target usernames/URLs")
    parser.add_argument("--max", "-m", type=int, default=10, help="Max actions")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    # Run worker
    worker = BotWorker(
        account_id=args.account,
        headless=args.headless
    )
    
    result = await worker.run_simple(
        task_type=TaskType(args.task),
        targets=args.targets,
        max_actions=args.max
    )
    
    print(f"\n{'='*50}")
    print(f"Worker Result: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Session ID: {result.session_id}")
    print(f"Actions: {result.actions_count}")
    print(f"Errors: {result.errors_count}")
    if result.error_message:
        print(f"Error: {result.error_message}")
    print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
