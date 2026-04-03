"""
Fallback Handler

Handles fallback from Playwright to Selenium when needed.
"""

import logging
from typing import Optional, Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class FallbackReason(Enum):
    """Reasons for triggering fallback."""
    PLAYWRIGHT_ERROR = "playwright_error"
    TIMEOUT = "timeout"
    DETECTION = "detection"
    RATE_LIMIT = "rate_limit"
    CAPTCHA = "captcha"
    UNKNOWN = "unknown"


class FallbackHandler:
    """
    Manages fallback from Playwright to Selenium.
    
    Features:
    - Automatic fallback on Playwright failures
    - Configurable fallback conditions
    - Callback notifications
    - Fallback statistics
    
    Example:
        from automation.playwright import InstagramBrowser as PlaywrightBrowser
        from automation.selenium import DriverManager
        
        handler = FallbackHandler()
        
        try:
            # Try Playwright first
            async with PlaywrightBrowser() as browser:
                await browser.login(username, password)
        except Exception as e:
            if handler.should_fallback(e):
                # Switch to Selenium
                selenium_driver = handler.create_selenium_fallback()
                # Continue with Selenium...
    """
    
    # Exception types that trigger fallback
    FALLBACK_EXCEPTIONS = [
        "TimeoutError",
        "TargetClosedError",
        "BrowserClosedError",
        "ConnectionClosedError",
    ]
    
    # Error messages that trigger fallback
    FALLBACK_MESSAGES = [
        "net::ERR_CONNECTION",
        "browser has disconnected",
        "page crashed",
        "navigation timeout",
        "execution context was destroyed",
    ]
    
    def __init__(
        self,
        max_fallback_attempts: int = 3,
        on_fallback_callback: Optional[Callable] = None
    ):
        """
        Initialize fallback handler.
        
        Args:
            max_fallback_attempts: Maximum fallback attempts before giving up
            on_fallback_callback: Called when fallback is triggered
        """
        self.max_attempts = max_fallback_attempts
        self.on_fallback = on_fallback_callback
        
        # Statistics
        self.fallback_count = 0
        self.fallback_history = []
        self._current_mode = "playwright"
        
        logger.info(f"FallbackHandler initialized (max_attempts={max_fallback_attempts})")
    
    def should_fallback(self, error: Exception) -> bool:
        """
        Determine if we should fall back to Selenium.
        
        Args:
            error: Exception that occurred
            
        Returns:
            True if fallback should be triggered
        """
        if self.fallback_count >= self.max_attempts:
            logger.warning("Max fallback attempts reached")
            return False
        
        error_name = type(error).__name__
        error_message = str(error).lower()
        
        # Check exception type
        if error_name in self.FALLBACK_EXCEPTIONS:
            return True
        
        # Check error message
        for message in self.FALLBACK_MESSAGES:
            if message.lower() in error_message:
                return True
        
        return False
    
    def trigger_fallback(
        self,
        reason: FallbackReason = FallbackReason.UNKNOWN,
        error: Optional[Exception] = None
    ) -> None:
        """
        Trigger fallback to Selenium.
        
        Args:
            reason: Reason for fallback
            error: Optional exception that caused fallback
        """
        self.fallback_count += 1
        self._current_mode = "selenium"
        
        fallback_info = {
            "reason": reason.value,
            "error": str(error) if error else None,
            "attempt": self.fallback_count,
        }
        self.fallback_history.append(fallback_info)
        
        logger.warning(
            f"Fallback triggered ({reason.value}): "
            f"attempt {self.fallback_count}/{self.max_attempts}"
        )
        
        # Notify callback
        if self.on_fallback:
            try:
                self.on_fallback(reason, error)
            except Exception as e:
                logger.error(f"Fallback callback error: {e}")
    
    def create_selenium_fallback(
        self,
        headless: bool = True,
        proxy: Optional[str] = None
    ) -> Any:
        """
        Create a Selenium WebDriver as fallback.
        
        Args:
            headless: Run in headless mode
            proxy: Optional proxy URL
            
        Returns:
            Configured Selenium WebDriver
        """
        try:
            from .driver_manager import DriverManager, BrowserType
            from .stealth_config import apply_stealth
            
            manager = DriverManager(
                browser_type=BrowserType.CHROME,
                headless=headless,
                proxy=proxy
            )
            
            driver = manager.create_driver()
            
            # Apply stealth
            try:
                apply_stealth(driver)
            except Exception as e:
                logger.warning(f"Could not apply stealth: {e}")
            
            logger.info("Created Selenium fallback driver")
            return driver
            
        except Exception as e:
            logger.error(f"Failed to create Selenium fallback: {e}")
            raise
    
    def reset(self) -> None:
        """Reset fallback state."""
        self.fallback_count = 0
        self._current_mode = "playwright"
        logger.info("Fallback state reset")
    
    @property
    def current_mode(self) -> str:
        """Get current automation mode."""
        return self._current_mode
    
    @property
    def is_using_fallback(self) -> bool:
        """Check if currently using Selenium fallback."""
        return self._current_mode == "selenium"
    
    def get_stats(self) -> dict:
        """Get fallback statistics."""
        return {
            "current_mode": self._current_mode,
            "fallback_count": self.fallback_count,
            "max_attempts": self.max_attempts,
            "history": self.fallback_history
        }


def auto_fallback(func: Callable) -> Callable:
    """
    Decorator to automatically handle Playwright to Selenium fallback.
    
    Example:
        @auto_fallback
        async def scrape_profile(browser, username):
            await browser.visit_profile(username)
            return await browser.extract_profile_info()
    """
    import functools
    import asyncio
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        handler = FallbackHandler()
        
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if handler.should_fallback(e):
                handler.trigger_fallback(
                    reason=FallbackReason.PLAYWRIGHT_ERROR,
                    error=e
                )
                
                # Create Selenium fallback
                driver = handler.create_selenium_fallback()
                
                try:
                    # Re-run with Selenium (caller needs to handle this)
                    kwargs["selenium_driver"] = driver
                    kwargs["fallback_mode"] = True
                    return await func(*args, **kwargs)
                finally:
                    driver.quit()
            raise
    
    return wrapper
