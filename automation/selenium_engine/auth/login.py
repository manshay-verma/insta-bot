"""
Instagram Login Flow (Selenium)

Handles login to Instagram using Selenium WebDriver.
"""

import time
import json
import logging
from typing import Optional, Any, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class InstagramLogin:
    """
    Handles Instagram login via Selenium.
    
    Features:
    - Username/password login
    - Cookie persistence (save/load)
    - 2FA handling (basic)
    - Popup dismissal
    
    Example:
        from selenium import webdriver
        
        driver = webdriver.Chrome()
        login = InstagramLogin(driver)
        
        # Login with credentials
        success = login.login("username", "password", cookie_path="cookies.json")
        
        if success:
            print("Logged in!")
    """
    
    INSTAGRAM_URL = "https://www.instagram.com/"
    LOGIN_URL = "https://www.instagram.com/accounts/login/"
    
    def __init__(self, driver: Any, timeout: int = 10):
        """
        Initialize login handler.
        
        Args:
            driver: Selenium WebDriver instance
            timeout: Default wait timeout in seconds
        """
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium not installed")
        
        self.driver = driver
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)
    
    def login(
        self,
        username: str,
        password: str,
        cookie_path: Optional[str] = None
    ) -> bool:
        """
        Login to Instagram.
        
        Args:
            username: Instagram username or email
            password: Instagram password
            cookie_path: Optional path to save/load cookies
            
        Returns:
            True if login successful
        """
        # Try loading from cookies first
        if cookie_path and self._load_cookies(cookie_path):
            if self._is_logged_in():
                logger.info("Logged in via saved cookies")
                return True
        
        # Login with credentials
        return self._login_with_credentials(username, password, cookie_path)
    
    def _login_with_credentials(
        self,
        username: str,
        password: str,
        cookie_path: Optional[str] = None
    ) -> bool:
        """Perform login with username/password."""
        try:
            # Navigate to login page
            self.driver.get(self.LOGIN_URL)
            time.sleep(2)
            
            # Dismiss cookie consent if present
            self._dismiss_cookie_popup()
            
            # Find and fill username field
            username_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            username_field.clear()
            self._human_type(username_field, username)
            
            # Find and fill password field
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.clear()
            self._human_type(password_field, password)
            
            # Click login button
            login_button = self.driver.find_element(
                By.CSS_SELECTOR, "button[type='submit']"
            )
            login_button.click()
            
            logger.info("Login form submitted, waiting for response...")
            time.sleep(5)
            
            # Check for various outcomes
            if self._check_for_2fa():
                logger.warning("2FA required - manual intervention needed")
                return False
            
            if self._check_for_challenge():
                logger.warning("Challenge/verification required")
                return False
            
            if self._is_logged_in():
                logger.info("Login successful!")
                
                # Handle post-login popups
                self._dismiss_save_login_popup()
                self._dismiss_notifications_popup()
                
                # Save cookies
                if cookie_path:
                    self._save_cookies(cookie_path)
                
                return True
            
            logger.error("Login failed - unknown reason")
            return False
            
        except TimeoutException:
            logger.error("Login timeout - elements not found")
            return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    def _human_type(self, element, text: str) -> None:
        """Type text with human-like delays."""
        import random
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
    
    def _dismiss_cookie_popup(self) -> None:
        """Dismiss cookie consent popup if present."""
        try:
            # Look for common cookie consent buttons
            selectors = [
                "button[class*='cookie']",
                "button:contains('Accept')",
                "button:contains('Allow')",
                "[data-testid='cookie-policy-dialog-accept-button']",
            ]
            
            for selector in selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed():
                            button.click()
                            logger.debug("Dismissed cookie popup")
                            time.sleep(1)
                            return
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"No cookie popup found: {e}")
    
    def _dismiss_save_login_popup(self) -> None:
        """Dismiss 'Save Login Info' popup."""
        try:
            not_now = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
            )
            not_now.click()
            logger.debug("Dismissed save login popup")
        except:
            pass
    
    def _dismiss_notifications_popup(self) -> None:
        """Dismiss notifications permission popup."""
        try:
            not_now = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
            )
            not_now.click()
            logger.debug("Dismissed notifications popup")
        except:
            pass
    
    def _check_for_2fa(self) -> bool:
        """Check if 2FA verification is required."""
        try:
            # Look for 2FA input
            self.driver.find_element(By.NAME, "verificationCode")
            return True
        except NoSuchElementException:
            return False
    
    def _check_for_challenge(self) -> bool:
        """Check if a security challenge is required."""
        current_url = self.driver.current_url
        return "challenge" in current_url or "checkpoint" in current_url
    
    def _is_logged_in(self) -> bool:
        """Check if currently logged in."""
        try:
            self.driver.get(self.INSTAGRAM_URL)
            time.sleep(2)
            
            # Check for logged-in indicators
            indicators = [
                "/direct/inbox/",  # DM icon
                "a[href='/direct/inbox/']",
                "[aria-label='Home']",
                "[aria-label='New post']",
            ]
            
            for indicator in indicators:
                try:
                    if indicator.startswith("/"):
                        # Check URL
                        if indicator in self.driver.page_source:
                            return True
                    else:
                        # Check element
                        elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                        if elements:
                            return True
                except:
                    continue
            
            # Check if we're not on login page
            if "accounts/login" not in self.driver.current_url:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return False
    
    def _save_cookies(self, cookie_path: str) -> None:
        """Save cookies to file."""
        try:
            cookies = self.driver.get_cookies()
            with open(cookie_path, 'w') as f:
                json.dump(cookies, f, indent=2)
            logger.info(f"Cookies saved to {cookie_path}")
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
    
    def _load_cookies(self, cookie_path: str) -> bool:
        """Load cookies from file."""
        try:
            if not Path(cookie_path).exists():
                return False
            
            with open(cookie_path, 'r') as f:
                cookies = json.load(f)
            
            # Navigate to Instagram first
            self.driver.get(self.INSTAGRAM_URL)
            time.sleep(1)
            
            # Add cookies
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"Could not add cookie: {e}")
            
            # Refresh to apply cookies
            self.driver.refresh()
            time.sleep(2)
            
            logger.info(f"Loaded cookies from {cookie_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return False
    
    def logout(self) -> bool:
        """Logout from Instagram."""
        try:
            # Navigate to profile settings
            self.driver.get("https://www.instagram.com/accounts/logout/")
            time.sleep(2)
            
            logger.info("Logged out")
            return True
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False
