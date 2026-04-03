"""
API Client for InstaBot Backend

Provides HTTP client wrapper for all backend REST API endpoints.
"""

import os
import requests
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class AccountStatus(Enum):
    """Bot account status choices."""
    ACTIVE = "active"
    PAUSED = "paused"
    BANNED = "banned"
    CHECKPOINT = "checkpoint"
    INACTIVE = "inactive"


class BotAction(Enum):
    """Bot control actions."""
    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"


@dataclass
class ApiResponse:
    """Standardized API response wrapper."""
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None
    status_code: int = 200


class InstaApiClient:
    """
    REST API client for backend communication.
    
    Usage:
        client = InstaApiClient(base_url="http://127.0.0.1:8000/api/v1")
        
        # Get account
        account = client.get_account(1)
        
        # Start session
        session = client.start_session(account_id=1)
        
        # Log action
        client.log_action(
            account_id=1,
            session_id=session.data['session_id'],
            action_type="follow",
            target_username="someuser",
            success=True
        )
    """
    
    def __init__(
        self,
        base_url: str = None,
        timeout: int = 30
    ):
        """
        Initialize API client.
        
        Args:
            base_url: Backend API base URL. Defaults to env var or localhost.
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url or os.getenv(
            "INSTABOT_API_URL",
            "http://127.0.0.1:8000/api/v1"
        )
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        params: Dict = None
    ) -> ApiResponse:
        """Make HTTP request to backend."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code >= 400:
                return ApiResponse(
                    success=False,
                    error=response.json().get("error", response.text),
                    status_code=response.status_code
                )
            
            return ApiResponse(
                success=True,
                data=response.json() if response.text else None,
                status_code=response.status_code
            )
            
        except requests.RequestException as e:
            return ApiResponse(
                success=False,
                error=str(e),
                status_code=0
            )
    
    # ==================== Health ====================
    
    def health_check(self) -> ApiResponse:
        """Check if backend is online."""
        return self._request("GET", "/health/")
    
    # ==================== Accounts ====================
    
    def get_account(self, account_id: int) -> ApiResponse:
        """Get bot account by ID."""
        return self._request("GET", f"/accounts/{account_id}/")
    
    def list_accounts(self, status: str = None) -> ApiResponse:
        """List all bot accounts, optionally filtered by status."""
        params = {"status": status} if status else None
        return self._request("GET", "/accounts/", params=params)
    
    def get_account_health(self, account_id: int) -> ApiResponse:
        """Get health status for an account."""
        return self._request("GET", f"/accounts/{account_id}/health/")
    
    def update_account_status(
        self,
        account_id: int,
        status: AccountStatus
    ) -> ApiResponse:
        """Update account status (active, paused, banned, etc.)."""
        return self._request(
            "PATCH",
            f"/accounts/{account_id}/",
            data={"status": status.value}
        )
    
    def update_cookies(
        self,
        account_id: int,
        cookies: List[Dict]
    ) -> ApiResponse:
        """Push session cookies to backend."""
        return self._request(
            "POST",
            f"/accounts/{account_id}/update_cookies/",
            data={"cookies": cookies}
        )
    
    # ==================== Sessions ====================
    
    def start_session(self, account_id: int) -> ApiResponse:
        """Start a new bot session."""
        return self._request(
            "POST",
            "/bots/control/",
            data={"action": BotAction.START.value, "account_id": account_id}
        )
    
    def stop_session(self, account_id: int) -> ApiResponse:
        """Stop all active sessions for an account."""
        return self._request(
            "POST",
            "/bots/control/",
            data={"action": BotAction.STOP.value, "account_id": account_id}
        )
    
    def pause_account(self, account_id: int) -> ApiResponse:
        """Pause an account."""
        return self._request(
            "POST",
            "/bots/control/",
            data={"action": BotAction.PAUSE.value, "account_id": account_id}
        )
    
    def resume_account(self, account_id: int) -> ApiResponse:
        """Resume a paused account."""
        return self._request(
            "POST",
            "/bots/control/",
            data={"action": BotAction.RESUME.value, "account_id": account_id}
        )
    
    def get_bot_status(self) -> ApiResponse:
        """Get status of all bots."""
        return self._request("GET", "/bots/status/")
    
    # ==================== Rate Limits ====================
    
    def get_rate_limits(self, account_id: int = None) -> ApiResponse:
        """Get rate limit status."""
        params = {"account_id": account_id} if account_id else None
        return self._request("GET", "/rate-limits/", params=params)
    
    # ==================== Action Logging ====================
    
    def log_action(
        self,
        account_id: int,
        action_type: str,
        session_id: int = None,
        target_username: str = None,
        target_url: str = None,
        success: bool = True,
        error_message: str = None,
        metadata: Dict = None
    ) -> ApiResponse:
        """
        Log an action performed by the bot.
        
        Args:
            account_id: Bot account ID
            action_type: One of: follow, unfollow, like, unlike, comment,
                        view_story, download, scrape_profile, scrape_posts
            session_id: Current session ID (optional)
            target_username: Target Instagram username
            target_url: Target post/story URL
            success: Whether action succeeded
            error_message: Error message if failed
            metadata: Additional action data
        """
        data = {
            "account": account_id,
            "action_type": action_type,
            "success": success,
        }
        
        if session_id:
            data["session"] = session_id
        if target_username:
            data["target_username"] = target_username
        if target_url:
            data["target_url"] = target_url
        if error_message:
            data["error_message"] = error_message
        if metadata:
            data["metadata"] = metadata
        
        return self._request("POST", "/actions/", data=data)
    
    # ==================== Proxies ====================
    
    def get_proxy(self, proxy_id: int) -> ApiResponse:
        """Get proxy by ID."""
        return self._request("GET", f"/proxies/{proxy_id}/")
    
    def list_proxies(self, is_active: bool = None) -> ApiResponse:
        """List all proxies."""
        params = {"is_active": str(is_active).lower()} if is_active is not None else None
        return self._request("GET", "/proxies/", params=params)
    
    # ==================== Analytics ====================
    
    def get_dashboard(self) -> ApiResponse:
        """Get dashboard summary."""
        return self._request("GET", "/analytics/dashboard/")
    
    def get_account_stats(self, account_id: int) -> ApiResponse:
        """Get stats for a specific account."""
        return self._request("GET", f"/analytics/accounts/{account_id}/stats/")


# Convenience function
def create_client(base_url: str = None) -> InstaApiClient:
    """Create API client instance."""
    return InstaApiClient(base_url=base_url)
