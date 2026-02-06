"""
Retry Handler Middleware

Custom retry logic for Instagram-specific errors.
"""

import logging
from typing import Optional, Set

from scrapy import signals
from scrapy.http import Request, Response
from scrapy.downloadermiddlewares.retry import RetryMiddleware as BaseRetryMiddleware

logger = logging.getLogger(__name__)


class RetryMiddleware(BaseRetryMiddleware):
    """
    Enhanced retry middleware for Instagram scraping.
    
    Features:
    - Custom HTTP status codes for retry
    - Instagram-specific error detection
    - Exponential backoff
    - Different retry strategies per error type
    """
    
    # Additional status codes to retry
    INSTAGRAM_RETRY_CODES = {
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
        520,  # Cloudflare origin error
        521,  # Cloudflare origin down
        522,  # Cloudflare connection timeout
        524,  # Cloudflare timeout
    }
    
    # Errors that should not be retried
    NO_RETRY_CODES = {
        400,  # Bad Request
        401,  # Unauthorized (need re-auth)
        403,  # Forbidden
        404,  # Not Found
    }
    
    def __init__(self, settings):
        """Initialize with settings."""
        super().__init__(settings)
        
        # Add our custom retry codes
        self.retry_http_codes: Set[int] = set(
            settings.getlist("RETRY_HTTP_CODES", [500, 502, 503, 504])
        )
        self.retry_http_codes.update(self.INSTAGRAM_RETRY_CODES)
        self.retry_http_codes -= self.NO_RETRY_CODES
        
        # Retry settings
        self.max_retry_times = settings.getint("RETRY_TIMES", 3)
        self.priority_adjust = settings.getint("RETRY_PRIORITY_ADJUST", -1)
        
        logger.info(
            f"RetryMiddleware initialized: "
            f"max_retries={self.max_retry_times}, codes={self.retry_http_codes}"
        )
    
    @classmethod
    def from_crawler(cls, crawler):
        """Create from crawler."""
        middleware = cls(crawler.settings)
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware
    
    def spider_opened(self, spider):
        """Log when spider opens."""
        spider.logger.info(f"RetryMiddleware active (max_retries={self.max_retry_times})")
    
    def process_response(
        self,
        request: Request,
        response: Response,
        spider
    ) -> Response:
        """
        Process response and check if retry is needed.
        
        Args:
            request: Original request
            response: Response received
            spider: Spider
            
        Returns:
            Response or retried Request
        """
        # Check Instagram-specific error conditions
        if self._is_instagram_error(response):
            reason = self._get_error_reason(response)
            return self._retry(request, reason, spider) or response
        
        # Standard HTTP status code check
        if response.status in self.retry_http_codes:
            reason = f"HTTP {response.status}"
            return self._retry(request, reason, spider) or response
        
        return response
    
    def _is_instagram_error(self, response: Response) -> bool:
        """
        Check if response contains Instagram-specific errors.
        
        Args:
            response: Response to check
            
        Returns:
            True if retry-able error detected
        """
        body = response.body.lower()
        
        # Rate limiting
        if b"please wait" in body or b"try again later" in body:
            return True
        
        # Temporary errors
        if b"oops, an error occurred" in body:
            return True
        
        # Empty or malformed response
        if response.status == 200 and len(response.body) < 100:
            # Unexpectedly short response
            return True
        
        return False
    
    def _get_error_reason(self, response: Response) -> str:
        """Get error reason from response."""
        body = response.body.lower()
        
        if b"please wait" in body:
            return "Rate limited (please wait)"
        if b"try again later" in body:
            return "Rate limited (try again)"
        if b"oops, an error occurred" in body:
            return "Instagram error page"
        if len(response.body) < 100:
            return "Empty/short response"
        
        return f"Instagram error (HTTP {response.status})"
    
    def _retry(
        self,
        request: Request,
        reason: str,
        spider
    ) -> Optional[Request]:
        """
        Retry a request with exponential backoff.
        
        Args:
            request: Request to retry
            reason: Reason for retry
            spider: Spider
            
        Returns:
            Retried request or None
        """
        retry_count = request.meta.get("retry_times", 0) + 1
        
        if retry_count <= self.max_retry_times:
            logger.info(
                f"Retrying {request.url} (attempt {retry_count}/{self.max_retry_times}): {reason}"
            )
            
            # Create new request
            retry_request = request.copy()
            retry_request.meta["retry_times"] = retry_count
            retry_request.priority = request.priority + self.priority_adjust
            
            # Add exponential backoff delay
            backoff_delay = 2 ** retry_count  # 2, 4, 8 seconds...
            retry_request.meta["download_delay"] = backoff_delay
            
            retry_request.dont_filter = True
            
            return retry_request
        
        logger.warning(
            f"Gave up retrying {request.url} after {self.max_retry_times} attempts: {reason}"
        )
        return None
    
    def process_exception(self, request: Request, exception, spider):
        """
        Handle request exceptions.
        
        Args:
            request: Failed request
            exception: Exception raised
            spider: Spider
            
        Returns:
            Retried request or None
        """
        # Get exception name
        exception_name = type(exception).__name__
        
        # Check if retryable
        retryable_exceptions = (
            "TimeoutError",
            "TCPTimedOutError",
            "DNSLookupError",
            "ConnectionRefusedError",
            "ConnectionLost",
        )
        
        if exception_name in retryable_exceptions:
            return self._retry(request, f"Exception: {exception_name}", spider)
        
        logger.error(f"Non-retryable exception for {request.url}: {exception}")
        return None
