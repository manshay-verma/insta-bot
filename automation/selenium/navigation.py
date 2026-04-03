"""
Instagram Navigation (Selenium)

Basic navigation functions for Instagram using Selenium.
"""

import time
import random
import logging
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

try:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import TimeoutException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class SeleniumNavigator:
    """
    Basic Instagram navigation using Selenium.
    
    Features:
    - Profile navigation
    - Feed scrolling
    - Explore page
    - Search functionality
    
    Example:
        from selenium import webdriver
        
        driver = webdriver.Chrome()
        nav = SeleniumNavigator(driver)
        
        nav.go_to_profile("instagram")
        nav.scroll_feed(5)
    """
    
    BASE_URL = "https://www.instagram.com"
    
    def __init__(self, driver: Any, timeout: int = 10):
        """
        Initialize navigator.
        
        Args:
            driver: Selenium WebDriver instance
            timeout: Default wait timeout
        """
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium not installed")
        
        self.driver = driver
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)
    
    def go_to_home(self) -> bool:
        """Navigate to home feed."""
        try:
            self.driver.get(self.BASE_URL)
            time.sleep(2)
            logger.info("Navigated to home feed")
            return True
        except Exception as e:
            logger.error(f"Failed to navigate home: {e}")
            return False
    
    def go_to_profile(self, username: str) -> bool:
        """
        Navigate to a user's profile.
        
        Args:
            username: Instagram username
            
        Returns:
            True if navigation successful
        """
        try:
            url = f"{self.BASE_URL}/{username.lstrip('@')}/"
            self.driver.get(url)
            time.sleep(2)
            
            # Check if profile exists
            if "Page Not Found" in self.driver.page_source:
                logger.warning(f"Profile not found: {username}")
                return False
            
            logger.info(f"Navigated to profile: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to profile: {e}")
            return False
    
    def go_to_explore(self) -> bool:
        """Navigate to Explore page."""
        try:
            self.driver.get(f"{self.BASE_URL}/explore/")
            time.sleep(2)
            logger.info("Navigated to Explore page")
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to Explore: {e}")
            return False
    
    def go_to_hashtag(self, hashtag: str) -> bool:
        """
        Navigate to a hashtag page.
        
        Args:
            hashtag: Hashtag (with or without #)
            
        Returns:
            True if navigation successful
        """
        try:
            tag = hashtag.lstrip("#")
            url = f"{self.BASE_URL}/explore/tags/{tag}/"
            self.driver.get(url)
            time.sleep(2)
            logger.info(f"Navigated to hashtag: #{tag}")
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to hashtag: {e}")
            return False
    
    def go_to_post(self, shortcode: str) -> bool:
        """
        Navigate to a specific post.
        
        Args:
            shortcode: Post shortcode
            
        Returns:
            True if navigation successful
        """
        try:
            url = f"{self.BASE_URL}/p/{shortcode}/"
            self.driver.get(url)
            time.sleep(2)
            logger.info(f"Navigated to post: {shortcode}")
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to post: {e}")
            return False
    
    def scroll_feed(self, times: int = 5) -> None:
        """
        Scroll the feed with human-like behavior.
        
        Args:
            times: Number of scroll actions
        """
        logger.info(f"Scrolling feed {times} times")
        
        for i in range(times):
            # Random scroll distance
            scroll_distance = random.randint(300, 800)
            
            self.driver.execute_script(
                f"window.scrollBy(0, {scroll_distance});"
            )
            
            # Random delay between scrolls
            delay = random.uniform(1.5, 4.0)
            time.sleep(delay)
            
            logger.debug(f"Scroll {i+1}/{times}")
    
    def scroll_to_bottom(self, max_scrolls: int = 10) -> None:
        """
        Scroll to the bottom of the page.
        
        Args:
            max_scrolls: Maximum scroll attempts
        """
        last_height = self.driver.execute_script(
            "return document.body.scrollHeight"
        )
        
        for _ in range(max_scrolls):
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(2)
            
            new_height = self.driver.execute_script(
                "return document.body.scrollHeight"
            )
            
            if new_height == last_height:
                break
            last_height = new_height
    
    def search(self, query: str, select_first: bool = False) -> bool:
        """
        Search for users/hashtags.
        
        Args:
            query: Search query
            select_first: Click on first result
            
        Returns:
            True if search successful
        """
        try:
            # Navigate to search page (click search icon first on mobile-like nav)
            self.driver.get(f"{self.BASE_URL}/explore/search/")
            time.sleep(2)
            
            # Or use direct URL with query
            # self.driver.get(f"{self.BASE_URL}/explore/search/?q={query}")
            
            # Find search input
            search_input = self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "input[placeholder*='Search']"
                ))
            )
            
            search_input.clear()
            search_input.send_keys(query)
            time.sleep(2)
            
            if select_first:
                # Click first result
                search_input.send_keys(Keys.RETURN)
                time.sleep(2)
            
            logger.info(f"Searched for: {query}")
            return True
            
        except TimeoutException:
            logger.error("Search input not found")
            return False
        except Exception as e:
            logger.error(f"Search error: {e}")
            return False
    
    def get_current_url(self) -> str:
        """Get current page URL."""
        return self.driver.current_url
    
    def refresh_page(self) -> None:
        """Refresh current page."""
        self.driver.refresh()
        time.sleep(2)
    
    def go_back(self) -> None:
        """Go back to previous page."""
        self.driver.back()
        time.sleep(2)
    
    def random_browse(self, duration_seconds: int = 60) -> None:
        """
        Browse randomly for a specified duration.
        
        Args:
            duration_seconds: How long to browse
        """
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            action = random.choice([
                self.scroll_feed,
                lambda: self.go_to_explore(),
                lambda: time.sleep(random.uniform(2, 5))
            ])
            
            try:
                if callable(action):
                    if action == self.scroll_feed:
                        action(random.randint(2, 5))
                    else:
                        action()
            except:
                pass
            
            time.sleep(random.uniform(1, 3))
        
        logger.info(f"Random browsing completed ({duration_seconds}s)")
