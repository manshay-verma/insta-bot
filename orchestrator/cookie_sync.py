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
from datetime import datetime, timezone
import time

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
        self.cookie_version = 0
    
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
            self.cookie_version = response.data.get("cookie_version", 0)
            
            if cookies:
                normalized = self.normalize_cookie_data(cookies)
                if normalized is not None and self.validate_cookie_list(normalized, allow_expired=True):
                    if not self.validate_cookie_list(normalized, allow_expired=False):
                        self.api_client.update_session_status(self.account_id, "expired")
                        logger.warning("Backend cookies for account %s are expired", self.account_id)
                        return None
                    logger.info("Loaded %d validated cookies for account %s", len(normalized), self.account_id)
                    return normalized
                self.api_client.update_session_status(self.account_id, "invalid")
                logger.warning("Backend cookies for account %s are malformed or invalid", self.account_id)
                return None
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
            normalized = self.normalize_cookie_data(cookies)
            if normalized is None or not self.validate_cookie_list(normalized, allow_expired=False):
                logger.warning("Cookie synchronization skipped for account %s: invalid cookie collection", self.account_id)
                return False
            response = self.api_client.update_cookies(
                self.account_id,
                normalized,
                expected_version=self.cookie_version,
            )
            
            if response.success:
                self.cookie_version = response.data.get("cookie_version", self.cookie_version)
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
            normalized = self.normalize_cookie_data(cookies)
            if normalized is None:
                logger.warning("Refused to export empty or malformed cookies")
                return False

            # Preserve the project's storage-state convention while exporting valid cookies.
            filepath.parent.mkdir(parents=True, exist_ok=True)
            storage_state = {
                "cookies": normalized,
                "origins": []
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(storage_state, f, indent=2)

            logger.info(f"Exported {len(normalized)} cookies to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting cookies to file: {e}")
            return False
    
    @staticmethod
    def normalize_cookie_data(data: Any) -> Optional[List[Dict]]:
        """Convert direct-list or storage-state data to a validated cookie list."""
        if isinstance(data, list):
            cookies = data
        elif isinstance(data, dict) and isinstance(data.get("cookies"), list):
            cookies = data["cookies"]
        else:
            logger.error("Invalid cookie data format")
            return None

        if not cookies:
            logger.warning("Cookie collection is empty")
            return None

        validated = []
        for cookie in cookies:
            if not isinstance(cookie, dict):
                logger.warning("Ignored malformed cookie entry")
                continue
            if not cookie.get("name") or not isinstance(cookie.get("value"), (str, int, float)):
                logger.warning("Ignored cookie without a valid name or value")
                continue
            validated.append(dict(cookie))

        if not validated:
            logger.warning("No valid cookies found in cookie collection")
            return None
        return validated

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
            
            cookies = self.normalize_cookie_data(data)
            if cookies is None:
                return None

            logger.info(f"Imported {len(cookies)} valid cookies from {filepath}")
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
            results["file"] = False
        
        return results
    
    # ==================== Validation ====================
    
    def validate_cookies(self, cookies: List[Dict]) -> bool:
        return self.validate_cookie_list(cookies, allow_expired=False)

    @staticmethod
    def validate_cookie_list(cookies: List[Dict], allow_expired: bool = False) -> bool:
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
            if not isinstance(cookie.get("name"), str) or not cookie["name"]:
                return False
            if not isinstance(cookie.get("value"), (str, int, float)):
                return False
            domain = str(cookie["domain"]).lower()
            if domain not in ("instagram.com", ".instagram.com") and not domain.endswith(".instagram.com"):
                return False
            if not allow_expired:
                expires = cookie.get("expires")
                if isinstance(expires, (int, float)) and expires > 0:
                    if expires <= time.time():
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
