"""
Proxy Rotation Middleware

Rotates proxies for each request to avoid IP-based rate limiting.
"""

import random
import logging
from typing import List, Optional

from scrapy import signals
from scrapy.http import Request

logger = logging.getLogger(__name__)


class ProxyRotationMiddleware:
    """
    Scrapy middleware to rotate proxies for requests.
    
    Settings:
        PROXY_LIST: List of proxy URLs
        PROXY_ROTATION_ENABLED: Enable/disable proxy rotation
    
    Proxy format:
        - http://host:port
        - http://user:pass@host:port
        - socks5://host:port
    """
    
    def __init__(self, proxy_list: List[str], enabled: bool = False):
        """
        Initialize the middleware.
        
        Args:
            proxy_list: List of proxy URLs
            enabled: Whether proxy rotation is enabled
        """
        self.proxy_list = proxy_list
        self.enabled = enabled and len(proxy_list) > 0
        self.failed_proxies = set()
        
        if self.enabled:
            logger.info(f"ProxyRotationMiddleware enabled with {len(proxy_list)} proxies")
        else:
            logger.info("ProxyRotationMiddleware disabled (no proxies configured)")
    
    @classmethod
    def from_crawler(cls, crawler):
        """Create middleware from crawler settings."""
        middleware = cls(
            proxy_list=crawler.settings.getlist("PROXY_LIST", []),
            enabled=crawler.settings.getbool("PROXY_ROTATION_ENABLED", False)
        )
        
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware
    
    def spider_opened(self, spider):
        """Log when spider opens."""
        spider.logger.info(
            f"Proxy rotation: {'enabled' if self.enabled else 'disabled'}"
        )
    
    def process_request(self, request: Request, spider):
        """
        Add proxy to request.
        
        Args:
            request: Scrapy request
            spider: Spider making the request
        """
        if not self.enabled:
            return None
        
        # Get available proxies (exclude failed ones)
        available = [p for p in self.proxy_list if p not in self.failed_proxies]
        
        if not available:
            # Reset failed proxies if all have failed
            logger.warning("All proxies failed, resetting list")
            self.failed_proxies.clear()
            available = self.proxy_list
        
        if available:
            proxy = random.choice(available)
            request.meta["proxy"] = proxy
            logger.debug(f"Using proxy: {self._mask_proxy(proxy)}")
        
        return None
    
    def process_exception(self, request: Request, exception, spider):
        """
        Handle request exceptions (potentially proxy failures).
        
        Args:
            request: Failed request
            exception: The exception
            spider: Spider
        """
        proxy = request.meta.get("proxy")
        
        if proxy and self._is_proxy_error(exception):
            self.failed_proxies.add(proxy)
            logger.warning(f"Proxy failed, marking as unavailable: {self._mask_proxy(proxy)}")
            
            # Retry with different proxy
            return request.replace(dont_filter=True)
        
        return None
    
    def _is_proxy_error(self, exception) -> bool:
        """Check if exception is proxy-related."""
        from twisted.internet.error import (
            ConnectionRefusedError,
            TCPTimedOutError,
            TimeoutError
        )
        
        proxy_errors = (
            ConnectionRefusedError,
            TCPTimedOutError,
            TimeoutError,
        )
        
        return isinstance(exception, proxy_errors)
    
    def _mask_proxy(self, proxy: str) -> str:
        """Mask proxy URL for logging (hide credentials)."""
        if "@" in proxy:
            # Has credentials, mask them
            parts = proxy.split("@")
            return f"***@{parts[-1]}"
        return proxy
    
    def get_stats(self) -> dict:
        """Get proxy statistics."""
        return {
            "total_proxies": len(self.proxy_list),
            "failed_proxies": len(self.failed_proxies),
            "available_proxies": len(self.proxy_list) - len(self.failed_proxies),
            "enabled": self.enabled
        }
