"""
Scrapy Adapter

Connects orchestrator with automation/scrapy_project/
Provides bulk scraping capabilities via Scrapy spiders.
"""

import logging
import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any

from .base_adapter import BaseAdapter, AdapterType, TaskType, TaskResult

# Add automation to path
automation_path = Path(__file__).parent.parent.parent / "automation"
scrapy_path = automation_path / "scrapy_project"
sys.path.insert(0, str(automation_path))
sys.path.insert(0, str(scrapy_path))

logger = logging.getLogger(__name__)


class ScrapyAdapter(BaseAdapter):
    """
    Adapter for Scrapy web scraping.
    
    Wraps:
    - automation/scrapy_project/instagram_scraper/spiders/hashtag_spider.py
    - automation/scrapy_project/instagram_scraper/spiders/profile_spider.py
    
    Supported Tasks:
    - SCRAPE_HASHTAG (bulk hashtag scraping)
    - SCRAPE_PROFILE (bulk profile scraping)
    
    Usage:
        adapter = ScrapyAdapter(api_client, account_id=1)
        await adapter.initialize()
        result = await adapter.execute(
            TaskType.SCRAPE_HASHTAG,
            ["travel", "photography"],
            max_posts=100
        )
        await adapter.cleanup()
    """
    
    adapter_type = AdapterType.SCRAPY
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scraped_items = []
        self._runner = None
    
    async def initialize(self) -> bool:
        """Initialize Scrapy runner."""
        try:
            from scrapy.crawler import CrawlerRunner
            from scrapy.utils.project import get_project_settings
            
            # Get Scrapy settings
            settings = get_project_settings()
            self._runner = CrawlerRunner(settings)
            
            self._initialized = True
            logger.info("Scrapy adapter initialized")
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import Scrapy: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Scrapy: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup Scrapy resources."""
        self.scraped_items = []
        self._runner = None
        self._initialized = False
        logger.info("Scrapy adapter cleaned up")
    
    def get_supported_tasks(self) -> List[TaskType]:
        """Get supported task types."""
        return [
            TaskType.SCRAPE_HASHTAG,
            TaskType.SCRAPE_PROFILE,
            TaskType.SCRAPE_FOLLOWERS,
        ]
    
    async def execute(
        self,
        task_type: TaskType,
        targets: List[str],
        **kwargs
    ) -> TaskResult:
        """Execute a Scrapy task."""
        if not self._initialized:
            return TaskResult(
                success=False,
                task_type=task_type,
                errors=["Adapter not initialized"]
            )
        
        handlers = {
            TaskType.SCRAPE_HASHTAG: self._scrape_hashtags,
            TaskType.SCRAPE_PROFILE: self._scrape_profiles,
            TaskType.SCRAPE_FOLLOWERS: self._scrape_followers,
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
    
    async def _scrape_hashtags(self, targets: List[str], **kwargs) -> TaskResult:
        """Scrape posts from hashtags."""
        max_posts = kwargs.get("max_posts", 50)
        all_items = []
        errors = []
        
        try:
            from instagram_scraper.spiders.hashtag_spider import HashtagSpider
            
            for hashtag in targets:
                try:
                    # Collect items via pipeline
                    items = await self._run_spider(
                        HashtagSpider,
                        hashtag=hashtag,
                        max_posts=max_posts
                    )
                    all_items.extend(items)
                    
                    if self.callback:
                        self.callback.on_scrape_posts(
                            target_username=f"#{hashtag}",
                            posts_count=len(items),
                            success=True
                        )
                except Exception as e:
                    errors.append(f"#{hashtag}: {str(e)}")
                    
        except ImportError:
            errors.append("HashtagSpider not available")
        
        return TaskResult(
            success=len(all_items) > 0,
            task_type=TaskType.SCRAPE_HASHTAG,
            data={"posts": all_items},
            items_processed=len(all_items),
            errors=errors
        )
    
    async def _scrape_profiles(self, targets: List[str], **kwargs) -> TaskResult:
        """Scrape profiles via Scrapy."""
        all_items = []
        errors = []
        
        try:
            from instagram_scraper.spiders.profile_spider import ProfileSpider
            
            for username in targets:
                try:
                    items = await self._run_spider(
                        ProfileSpider,
                        username=username
                    )
                    all_items.extend(items)
                    
                    if self.callback:
                        self.callback.on_scrape_profile(
                            target_username=username,
                            success=True,
                            profile_data=items[0] if items else None
                        )
                except Exception as e:
                    errors.append(f"@{username}: {str(e)}")
                    
        except ImportError:
            errors.append("ProfileSpider not available")
        
        return TaskResult(
            success=len(all_items) > 0,
            task_type=TaskType.SCRAPE_PROFILE,
            data={"profiles": all_items},
            items_processed=len(all_items),
            errors=errors
        )
    
    async def _scrape_followers(self, targets: List[str], **kwargs) -> TaskResult:
        """Scrape followers list."""
        max_followers = kwargs.get("max_followers", 100)
        all_items = []
        errors = []
        
        # Placeholder - spider needs to be implemented
        errors.append("FollowersSpider not implemented yet")
        
        return TaskResult(
            success=False,
            task_type=TaskType.SCRAPE_FOLLOWERS,
            data={"followers": all_items},
            items_processed=0,
            errors=errors
        )
    
    async def _run_spider(self, spider_class, **spider_kwargs) -> List[Dict]:
        """
        Run a Scrapy spider and collect results.
        
        Args:
            spider_class: Spider class to run
            **spider_kwargs: Arguments to pass to spider
            
        Returns:
            List of scraped items
        """
        collected_items = []
        
        # Custom pipeline to collect items
        class CollectorPipeline:
            def process_item(self, item, spider):
                collected_items.append(dict(item))
                return item
        
        try:
            from twisted.internet import reactor
            from scrapy.crawler import CrawlerRunner
            from scrapy import signals
            
            # Create runner with custom settings
            runner = CrawlerRunner({
                'ITEM_PIPELINES': {'__main__.CollectorPipeline': 300},
                'LOG_ENABLED': False,
            })
            
            # Run crawler
            deferred = runner.crawl(spider_class, **spider_kwargs)
            
            # Wait for completion (with timeout)
            await asyncio.wait_for(
                asyncio.wrap_future(deferred),
                timeout=300  # 5 minute timeout
            )
            
        except Exception as e:
            logger.error(f"Spider execution failed: {e}")
        
        return collected_items
