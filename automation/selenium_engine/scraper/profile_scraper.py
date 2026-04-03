"""
Profile Scraper (Selenium)

Scrapes Instagram profile data using Selenium WebDriver.
"""

import re
import time
import logging
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

try:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class ProfileScraper:
    """
    Scrapes Instagram profile data using Selenium.
    
    Features:
    - Extract profile info (bio, stats)
    - Handle public and private profiles
    - Multiple extraction strategies
    
    Example:
        from selenium import webdriver
        
        driver = webdriver.Chrome()
        scraper = ProfileScraper(driver)
        
        profile = scraper.scrape_profile("instagram")
        print(f"Followers: {profile['followers_count']}")
    """
    
    BASE_URL = "https://www.instagram.com"
    
    def __init__(self, driver: Any, timeout: int = 10):
        """
        Initialize scraper.
        
        Args:
            driver: Selenium WebDriver instance
            timeout: Wait timeout
        """
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium not installed")
        
        self.driver = driver
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)
    
    def scrape_profile(self, username: str) -> Optional[Dict]:
        """
        Scrape profile data for a user.
        
        Args:
            username: Instagram username
            
        Returns:
            Dictionary with profile data or None
        """
        try:
            # Navigate to profile
            url = f"{self.BASE_URL}/{username.lstrip('@')}/"
            self.driver.get(url)
            time.sleep(2)
            
            # Check if profile exists
            if "Page Not Found" in self.driver.page_source:
                logger.warning(f"Profile not found: {username}")
                return None
            
            # Extract data
            profile = {
                "username": username,
                "url": url,
            }
            
            # Try multiple extraction methods
            profile.update(self._extract_from_meta_tags())
            profile.update(self._extract_from_page())
            profile.update(self._extract_stats())
            
            logger.info(f"Scraped profile: @{username}")
            return profile
            
        except Exception as e:
            logger.error(f"Failed to scrape profile: {e}")
            return None
    
    def _extract_from_meta_tags(self) -> Dict:
        """Extract data from meta tags."""
        data = {}
        
        try:
            # OG description often has follower count
            og_desc = self.driver.find_element(
                By.CSS_SELECTOR, "meta[property='og:description']"
            )
            description = og_desc.get_attribute("content")
            
            # Parse description: "X Followers, Y Following, Z Posts - ..."
            if description:
                data["meta_description"] = description
                
                # Extract counts
                followers_match = re.search(r'([\d,.]+[KMB]?)\s*Followers', description, re.I)
                following_match = re.search(r'([\d,.]+[KMB]?)\s*Following', description, re.I)
                posts_match = re.search(r'([\d,.]+[KMB]?)\s*Posts', description, re.I)
                
                if followers_match:
                    data["followers_count"] = self._parse_count(followers_match.group(1))
                if following_match:
                    data["following_count"] = self._parse_count(following_match.group(1))
                if posts_match:
                    data["posts_count"] = self._parse_count(posts_match.group(1))
            
            # OG title often has full name
            og_title = self.driver.find_element(
                By.CSS_SELECTOR, "meta[property='og:title']"
            )
            title = og_title.get_attribute("content")
            if title:
                # Parse: "Full Name (@username) • Instagram photos and videos"
                name_match = re.match(r'^([^(@]+)', title)
                if name_match:
                    data["full_name"] = name_match.group(1).strip()
                    
        except Exception as e:
            logger.debug(f"Meta extraction error: {e}")
        
        return data
    
    def _extract_from_page(self) -> Dict:
        """Extract data from page elements."""
        data = {}
        
        try:
            # Bio
            bio_selectors = [
                "div.-vDIg span",
                "header section div span",
                "[class*='_aa_'] span:not([class])",
            ]
            
            for selector in bio_selectors:
                try:
                    bio_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in bio_elements:
                        text = elem.text.strip()
                        if text and len(text) > 20 and not text.startswith("http"):
                            data["bio"] = text
                            break
                    if "bio" in data:
                        break
                except:
                    continue
            
            # Profile picture
            try:
                img = self.driver.find_element(
                    By.CSS_SELECTOR, "header img[alt*='profile']"
                )
                data["profile_pic_url"] = img.get_attribute("src")
            except:
                pass
            
            # Check if private
            try:
                if "This Account is Private" in self.driver.page_source:
                    data["is_private"] = True
                else:
                    data["is_private"] = False
            except:
                pass
            
            # Check if verified
            try:
                verified = self.driver.find_elements(
                    By.CSS_SELECTOR, "[aria-label='Verified']"
                )
                data["is_verified"] = len(verified) > 0
            except:
                data["is_verified"] = False
                
        except Exception as e:
            logger.debug(f"Page extraction error: {e}")
        
        return data
    
    def _extract_stats(self) -> Dict:
        """Extract follower/following/post counts from page."""
        data = {}
        
        try:
            # Look for stat links
            stat_links = self.driver.find_elements(
                By.CSS_SELECTOR, "header section ul li"
            )
            
            for link in stat_links:
                text = link.text.lower()
                
                if "posts" in text or "post" in text:
                    count = self._extract_number_from_text(link.text)
                    if count is not None and "posts_count" not in data:
                        data["posts_count"] = count
                        
                elif "followers" in text:
                    count = self._extract_number_from_text(link.text)
                    if count is not None and "followers_count" not in data:
                        data["followers_count"] = count
                        
                elif "following" in text:
                    count = self._extract_number_from_text(link.text)
                    if count is not None and "following_count" not in data:
                        data["following_count"] = count
                        
        except Exception as e:
            logger.debug(f"Stats extraction error: {e}")
        
        return data
    
    def _extract_number_from_text(self, text: str) -> Optional[int]:
        """Extract number from text like '1,234 followers'."""
        match = re.search(r'([\d,.]+[KMB]?)', text)
        if match:
            return self._parse_count(match.group(1))
        return None
    
    def _parse_count(self, count_str: str) -> Optional[int]:
        """Parse count strings like '1.5M', '10K', etc."""
        if not count_str:
            return None
        
        count_str = count_str.strip().upper()
        count_str = count_str.replace(",", "")
        
        try:
            if "K" in count_str:
                return int(float(count_str.replace("K", "")) * 1000)
            elif "M" in count_str:
                return int(float(count_str.replace("M", "")) * 1000000)
            elif "B" in count_str:
                return int(float(count_str.replace("B", "")) * 1000000000)
            else:
                return int(float(count_str))
        except (ValueError, AttributeError):
            return None
    
    def scrape_multiple(self, usernames: list) -> list:
        """
        Scrape multiple profiles.
        
        Args:
            usernames: List of usernames
            
        Returns:
            List of profile dictionaries
        """
        profiles = []
        
        for username in usernames:
            profile = self.scrape_profile(username)
            if profile:
                profiles.append(profile)
            time.sleep(2)  # Be nice
        
        return profiles
