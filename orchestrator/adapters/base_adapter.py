"""
Base Adapter

Abstract base class for all automation module adapters.
Provides unified interface for orchestrator to interact with any automation backend.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class AdapterType(Enum):
    """Supported adapter types."""
    PLAYWRIGHT = "playwright"
    SELENIUM = "selenium"
    SCRAPY = "scrapy"
    DOWNLOADER = "downloader"
    SAFETY = "safety"


class TaskType(Enum):
    """Unified task types across all adapters."""
    # Browser actions (Playwright/Selenium)
    LOGIN = "login"
    SCRAPE_PROFILE = "scrape_profile"
    SCRAPE_POSTS = "scrape_posts"
    LIKE_POSTS = "like_posts"
    UNLIKE_POSTS = "unlike_posts"
    FOLLOW_USERS = "follow_users"
    UNFOLLOW_USERS = "unfollow_users"
    VIEW_STORIES = "view_stories"
    COMMENT = "comment"
    
    # Scrapy tasks
    SCRAPE_HASHTAG = "scrape_hashtag"
    SCRAPE_FOLLOWERS = "scrape_followers"
    
    # Downloader tasks
    DOWNLOAD_IMAGE = "download_image"
    DOWNLOAD_VIDEO = "download_video"
    DOWNLOAD_CAROUSEL = "download_carousel"
    DOWNLOAD_STORY = "download_story"
    BULK_DOWNLOAD = "bulk_download"
    UPLOAD_S3 = "upload_s3"
    
    # Safety tasks
    CHECK_RATE_LIMIT = "check_rate_limit"
    GET_DELAY = "get_delay"
    CHECK_HEALTH = "check_health"


@dataclass
class TaskResult:
    """Result from adapter task execution."""
    success: bool
    task_type: TaskType
    data: Optional[Dict] = None
    items_processed: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class BaseAdapter(ABC):
    """
    Abstract base class for automation adapters.
    
    All adapters must implement:
    - initialize(): Setup the automation module
    - cleanup(): Teardown resources
    - execute(): Run a specific task
    - get_supported_tasks(): List supported task types
    """
    
    adapter_type: AdapterType = None
    
    def __init__(
        self,
        api_client,  # InstaApiClient
        account_id: int,
        callback = None,  # ActionCallback
        config: Dict = None
    ):
        """
        Initialize adapter.
        
        Args:
            api_client: Backend API client
            account_id: Bot account ID
            callback: Action callback for logging
            config: Additional configuration
        """
        self.api_client = api_client
        self.account_id = account_id
        self.callback = callback
        self.config = config or {}
        
        self._initialized = False
        self._account_data = None
        
        logger.info(f"Created {self.__class__.__name__} for account {account_id}")
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the automation module.
        
        Returns:
            True if initialization successful
        """
        pass
    
    @abstractmethod
    async def cleanup(self):
        """Cleanup resources and close connections."""
        pass
    
    @abstractmethod
    async def execute(self, task_type: TaskType, targets: List[str], **kwargs) -> TaskResult:
        """
        Execute a task.
        
        Args:
            task_type: Type of task to execute
            targets: List of usernames, URLs, or hashtags
            **kwargs: Additional task-specific parameters
            
        Returns:
            TaskResult with execution results
        """
        pass
    
    @abstractmethod
    def get_supported_tasks(self) -> List[TaskType]:
        """
        Get list of supported task types.
        
        Returns:
            List of TaskType enums this adapter supports
        """
        pass
    
    async def fetch_account(self) -> Optional[Dict]:
        """Fetch account data from backend."""
        response = self.api_client.get_account(self.account_id)
        if response.success:
            self._account_data = response.data
            return self._account_data
        logger.error(f"Failed to fetch account: {response.error}")
        return None
    
    def get_proxy_config(self) -> Optional[Dict]:
        """Build proxy config from account data."""
        if not self._account_data:
            return None
        
        proxy_data = self._account_data.get("proxy")
        if not proxy_data:
            return None
        
        return {
            "server": f"{proxy_data['protocol']}://{proxy_data['host']}:{proxy_data['port']}",
            "username": proxy_data.get("username"),
            "password": proxy_data.get("password"),
        }
    
    def supports_task(self, task_type: TaskType) -> bool:
        """Check if adapter supports a task type."""
        return task_type in self.get_supported_tasks()
    
    @property
    def is_initialized(self) -> bool:
        """Check if adapter is initialized."""
        return self._initialized
