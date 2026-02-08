"""
Cookie Synchronization

Manages cookies between automation file storage and backend database.
Ensures session persistence across bot restarts.
"""

import json
import os
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

from .api_client import InstaApiClient


logger = logging.getLogger(__name__)


class CookieSync:
    """
    Cookie synchronization between automation and backend.
    
    Handles:
    - Loading cookies from backend DB
    - Saving cookies to backend DB
    - Exporting cookies to JSON file (for Playwright)
    - Importing cookies from JSON file
    
    Usage:
        sync = CookieSync(api_client, account_id=1)
        
        # Load from backend
        cookies = sync.load_from_backend()
        
        # After login, save new cookies
        sync.save_to_backend(new_cookies)
        
        # Export to file for Playwright
        sync.export_to_file("/path/to/cookies.json")
    """
    
    DEFAULT_COOKIE_DIR = Path("cookies")
    
    def __init__(
        self,
        api_client: InstaApiClient,
        account_id: int,
        cookie_dir: Path = None
    ):
        """
        Initialize cookie sync.
        
        Args:
            api_client: Backend API client
            account_id: Bot account ID
            cookie_dir: Directory for cookie files
        """
        self.api_client = api_client
        self.account_id = account_id
        self.cookie_dir = cookie_dir or self.DEFAULT_COOKIE_DIR
        
        # Ensure cookie directory exists
        self.cookie_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def cookie_file_path(self) -> Path:
        """Get default cookie file path for this account."""
        return self.cookie_dir / f"account_{self.account_id}_cookies.json"
    
    # ==================== Backend Operations ====================
    
    def load_from_backend(self) -> Optional[List[Dict]]:
        """
        Fetch cookies from backend database.
        
        Returns:
            List of cookie dicts, or None if not found
        """
        try:
            response = self.api_client.get_account(self.account_id)
            
            if not response.success:
                logger.warning(f"Failed to fetch account: {response.error}")
                return None
            
            cookies = response.data.get("cookies_json")
            
            if cookies:
                logger.info(f"Loaded {len(cookies)} cookies from backend for account {self.account_id}")
                return cookies
            else:
                logger.info(f"No cookies found in backend for account {self.account_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading cookies from backend: {e}")
            return None
    
    def save_to_backend(self, cookies: List[Dict]) -> bool:
        """
        Push cookies to backend database.
        
        Args:
            cookies: List of cookie dicts from browser
            
        Returns:
            True if saved successfully
        """
        try:
            response = self.api_client.update_cookies(self.account_id, cookies)
            
            if response.success:
                logger.info(f"Saved {len(cookies)} cookies to backend for account {self.account_id}")
                return True
            else:
                logger.error(f"Failed to save cookies: {response.error}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving cookies to backend: {e}")
            return False
    
    # ==================== File Operations ====================
    
    def export_to_file(
        self,
        cookies: List[Dict],
        filepath: Path = None
    ) -> bool:
        """
        Save cookies to JSON file for Playwright.
        
        Args:
            cookies: List of cookie dicts
            filepath: Output file path (uses default if None)
            
        Returns:
            True if saved successfully
        """
        filepath = Path(filepath) if filepath else self.cookie_file_path
        
        try:
            # Ensure directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Format for Playwright storage state
            storage_state = {
                "cookies": cookies,
                "origins": []
            }
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(storage_state, f, indent=2)
            
            logger.info(f"Exported {len(cookies)} cookies to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting cookies to file: {e}")
            return False
    
    def import_from_file(self, filepath: Path = None) -> Optional[List[Dict]]:
        """
        Load cookies from JSON file.
        
        Args:
            filepath: Input file path (uses default if None)
            
        Returns:
            List of cookie dicts, or None if not found
        """
        filepath = Path(filepath) if filepath else self.cookie_file_path
        
        if not filepath.exists():
            logger.warning(f"Cookie file not found: {filepath}")
            return None
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Handle both formats: direct list or Playwright storage state
            if isinstance(data, list):
                cookies = data
            elif isinstance(data, dict) and "cookies" in data:
                cookies = data["cookies"]
            else:
                logger.error("Invalid cookie file format")
                return None
            
            logger.info(f"Imported {len(cookies)} cookies from {filepath}")
            return cookies
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in cookie file: {e}")
            return None
        except Exception as e:
            logger.error(f"Error importing cookies from file: {e}")
            return None
    
    # ==================== Sync Operations ====================
    
    def sync_to_file(self) -> bool:
        """
        Pull cookies from backend and save to file.
        
        Returns:
            True if synced successfully
        """
        cookies = self.load_from_backend()
        if cookies:
            return self.export_to_file(cookies)
        return False
    
    def sync_to_backend(self) -> bool:
        """
        Push cookies from file to backend.
        
        Returns:
            True if synced successfully
        """
        cookies = self.import_from_file()
        if cookies:
            return self.save_to_backend(cookies)
        return False
    
    def full_sync(
        self,
        browser_cookies: List[Dict] = None
    ) -> Dict[str, bool]:
        """
        Perform full sync: save to both backend and file.
        
        Args:
            browser_cookies: Fresh cookies from browser session
            
        Returns:
            Dict with sync results
        """
        results = {
            "backend": False,
            "file": False
        }
        
        if browser_cookies:
            results["backend"] = self.save_to_backend(browser_cookies)
            results["file"] = self.export_to_file(browser_cookies)
        
        return results
    
    # ==================== Validation ====================
    
    def validate_cookies(self, cookies: List[Dict]) -> bool:
        """
        Validate cookie structure.
        
        Args:
            cookies: List of cookie dicts
            
        Returns:
            True if cookies appear valid
        """
        if not cookies:
            return False
        
        required_keys = {"name", "value", "domain"}
        
        for cookie in cookies:
            if not isinstance(cookie, dict):
                return False
            if not required_keys.issubset(cookie.keys()):
                return False
        
        # Check for Instagram-specific cookies
        cookie_names = {c.get("name") for c in cookies}
        essential_cookies = {"sessionid", "csrftoken"}
        
        if not essential_cookies.issubset(cookie_names):
            logger.warning("Missing essential Instagram cookies (sessionid, csrftoken)")
            return False
        
        return True
    
    def get_cookie_info(self, cookies: List[Dict]) -> Dict[str, Any]:
        """
        Get information about cookies.
        
        Args:
            cookies: List of cookie dicts
            
        Returns:
            Cookie summary info
        """
        if not cookies:
            return {"count": 0, "valid": False}
        
        cookie_names = [c.get("name") for c in cookies]
        domains = set(c.get("domain") for c in cookies)
        
        # Check for session cookie
        has_session = "sessionid" in cookie_names
        
        return {
            "count": len(cookies),
            "valid": self.validate_cookies(cookies),
            "has_session": has_session,
            "domains": list(domains),
            "cookie_names": cookie_names,
        }
