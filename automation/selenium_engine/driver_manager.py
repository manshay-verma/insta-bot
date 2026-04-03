"""
Browser Driver Manager

Handles Selenium WebDriver setup with automatic driver management.
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum
from contextlib import contextmanager

logger = logging.getLogger(__name__)

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.firefox.service import Service as FirefoxService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium not installed. Install with: pip install selenium")

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.firefox import GeckoDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False
    logger.warning("webdriver-manager not installed. Install with: pip install webdriver-manager")


class BrowserType(Enum):
    """Supported browser types."""
    CHROME = "chrome"
    FIREFOX = "firefox"


class DriverManager:
    """
    Manages Selenium WebDriver instances.
    
    Features:
    - Automatic driver download via webdriver-manager
    - Support for Chrome and Firefox
    - Configurable options (headless, proxy, etc.)
    - Context manager support
    
    Example:
        manager = DriverManager(browser_type=BrowserType.CHROME, headless=True)
        
        with manager.get_driver() as driver:
            driver.get("https://instagram.com")
            # Do stuff
    """
    
    def __init__(
        self,
        browser_type: BrowserType = BrowserType.CHROME,
        headless: bool = True,
        proxy: Optional[str] = None,
        user_agent: Optional[str] = None,
        window_size: tuple = (1920, 1080)
    ):
        """
        Initialize the driver manager.
        
        Args:
            browser_type: Browser to use (Chrome or Firefox)
            headless: Run in headless mode
            proxy: Optional proxy URL (http://host:port)
            user_agent: Optional custom user agent
            window_size: Browser window size (width, height)
        """
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium not installed. Run: pip install selenium")
        
        self.browser_type = browser_type
        self.headless = headless
        self.proxy = proxy
        self.user_agent = user_agent or self._default_user_agent()
        self.window_size = window_size
        
        self._driver = None
        
        logger.info(
            f"DriverManager initialized: {browser_type.value}, "
            f"headless={headless}"
        )
    
    def _default_user_agent(self) -> str:
        """Get default user agent string."""
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    
    def _get_chrome_options(self) -> "ChromeOptions":
        """Configure Chrome options."""
        options = ChromeOptions()
        
        if self.headless:
            options.add_argument("--headless=new")
        
        options.add_argument(f"--window-size={self.window_size[0]},{self.window_size[1]}")
        options.add_argument(f"--user-agent={self.user_agent}")
        
        # Anti-detection arguments
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        if self.proxy:
            options.add_argument(f"--proxy-server={self.proxy}")
        
        return options
    
    def _get_firefox_options(self) -> "FirefoxOptions":
        """Configure Firefox options."""
        options = FirefoxOptions()
        
        if self.headless:
            options.add_argument("--headless")
        
        options.add_argument(f"--width={self.window_size[0]}")
        options.add_argument(f"--height={self.window_size[1]}")
        
        # Set user agent
        options.set_preference("general.useragent.override", self.user_agent)
        
        # Privacy settings
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        
        if self.proxy:
            # Parse proxy
            proxy_parts = self.proxy.replace("http://", "").replace("https://", "")
            host, port = proxy_parts.split(":")
            options.set_preference("network.proxy.type", 1)
            options.set_preference("network.proxy.http", host)
            options.set_preference("network.proxy.http_port", int(port))
            options.set_preference("network.proxy.ssl", host)
            options.set_preference("network.proxy.ssl_port", int(port))
        
        return options
    
    def create_driver(self) -> Any:
        """
        Create a new WebDriver instance.
        
        Returns:
            WebDriver instance
        """
        if self.browser_type == BrowserType.CHROME:
            return self._create_chrome_driver()
        elif self.browser_type == BrowserType.FIREFOX:
            return self._create_firefox_driver()
        else:
            raise ValueError(f"Unsupported browser: {self.browser_type}")
    
    def _create_chrome_driver(self) -> Any:
        """Create Chrome WebDriver."""
        options = self._get_chrome_options()
        
        if WEBDRIVER_MANAGER_AVAILABLE:
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)
        
        logger.info("Chrome WebDriver created")
        return driver
    
    def _create_firefox_driver(self) -> Any:
        """Create Firefox WebDriver."""
        options = self._get_firefox_options()
        
        if WEBDRIVER_MANAGER_AVAILABLE:
            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)
        else:
            driver = webdriver.Firefox(options=options)
        
        logger.info("Firefox WebDriver created")
        return driver
    
    @contextmanager
    def get_driver(self):
        """
        Context manager for WebDriver.
        
        Usage:
            with manager.get_driver() as driver:
                driver.get("https://example.com")
        """
        driver = self.create_driver()
        try:
            yield driver
        finally:
            driver.quit()
            logger.info("WebDriver closed")
    
    def get_persistent_driver(self) -> Any:
        """
        Get a persistent driver instance (must be manually closed).
        
        Returns:
            WebDriver instance
        """
        if self._driver is None:
            self._driver = self.create_driver()
        return self._driver
    
    def close(self) -> None:
        """Close the persistent driver if it exists."""
        if self._driver:
            self._driver.quit()
            self._driver = None
            logger.info("Persistent WebDriver closed")
