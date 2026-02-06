"""
Request Throttling Middleware

Custom throttling for Instagram-specific rate limiting.
"""

import random
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from scrapy import signals
from scrapy.http import Request, Response

logger = logging.getLogger(__name__)


class ThrottleMiddleware:
    """
    Spider middleware for Instagram-specific request throttling.
    
    Features:
    - Different delays for different endpoints
    - Random jitter for natural behavior
    - Slowdown on rate limit signals
    """
    
    # Default delays per endpoint type (seconds)
    ENDPOINT_DELAYS = {
        "graphql": 5.0,      # GraphQL API calls
        "profile": 3.0,      # Profile pages
        "post": 3.0,         # Post pages
        "hashtag": 4.0,      # Hashtag pages
        "explore": 4.0,      # Explore page
        "default": 3.0       # Other requests
    }
    
    def __init__(self, base_delay: float = 3.0, jitter: float = 0.5):
        """
        Initialize the middleware.
        
        Args:
            base_delay: Base delay between requests
            jitter: Random variation (0-1, multiplied by delay)
        """
        self.base_delay = base_delay
        self.jitter = jitter
        self.last_request_time: Dict[str, datetime] = {}
        self.slowdown_until: Optional[datetime] = None
        self.slowdown_factor = 1.0
    
    @classmethod
    def from_crawler(cls, crawler):
        """Create middleware from crawler settings."""
        middleware = cls(
            base_delay=crawler.settings.getfloat("DOWNLOAD_DELAY", 3.0),
            jitter=0.5
        )
        
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware
    
    def spider_opened(self, spider):
        """Log when spider opens."""
        spider.logger.info(f"ThrottleMiddleware active (base_delay={self.base_delay}s)")
    
    def process_spider_input(self, response: Response, spider):
        """
        Process response and check for rate limit signals.
        
        Args:
            response: Scrapy response
            spider: Spider
        """
        # Check for rate limit indicators
        if response.status == 429:
            self._handle_rate_limit(response, spider)
        
        # Check response body for rate limit text
        if b"wait a few minutes" in response.body.lower():
            self._handle_rate_limit(response, spider)
        
        return None
    
    def process_spider_output(self, response: Response, result, spider):
        """
        Process spider output and add delays to requests.
        
        Args:
            response: Scrapy response
            result: Spider output (items and requests)
            spider: Spider
        """
        for item in result:
            if isinstance(item, Request):
                # Add delay info to request
                endpoint_type = self._get_endpoint_type(item.url)
                delay = self._calculate_delay(endpoint_type)
                item.meta["download_delay"] = delay
            
            yield item
    
    def _get_endpoint_type(self, url: str) -> str:
        """Determine endpoint type from URL."""
        if "graphql" in url:
            return "graphql"
        elif "/p/" in url:
            return "post"
        elif "/explore/tags/" in url:
            return "hashtag"
        elif "/explore/" in url:
            return "explore"
        elif url.count("/") == 4 and not any(x in url for x in ["/p/", "/explore/"]):
            return "profile"
        return "default"
    
    def _calculate_delay(self, endpoint_type: str) -> float:
        """
        Calculate delay for an endpoint type.
        
        Args:
            endpoint_type: Type of endpoint
            
        Returns:
            Delay in seconds
        """
        base = self.ENDPOINT_DELAYS.get(endpoint_type, self.base_delay)
        
        # Apply slowdown factor if active
        if self.slowdown_until and datetime.now() < self.slowdown_until:
            base *= self.slowdown_factor
        
        # Add jitter
        jitter_amount = base * self.jitter
        delay = base + random.uniform(-jitter_amount, jitter_amount)
        
        return max(1.0, delay)  # Minimum 1 second
    
    def _handle_rate_limit(self, response: Response, spider):
        """
        Handle rate limit detection.
        
        Args:
            response: Rate limited response
            spider: Spider
        """
        logger.warning(f"Rate limit detected for {response.url}")
        
        # Increase slowdown
        self.slowdown_factor = min(5.0, self.slowdown_factor * 1.5)
        self.slowdown_until = datetime.now() + timedelta(minutes=5)
        
        spider.logger.warning(
            f"Slowing down by {self.slowdown_factor}x for 5 minutes"
        )
