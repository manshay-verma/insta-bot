"""
Action Callbacks for Instagram Automation

Provides event hooks that automation scripts can trigger to report
actions back to the backend for logging and analytics.
"""

import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .api_client import InstaApiClient, ApiResponse


logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Supported action types matching backend ActionLog model."""
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    LIKE = "like"
    UNLIKE = "unlike"
    COMMENT = "comment"
    VIEW_STORY = "view_story"
    DOWNLOAD = "download"
    SCRAPE_PROFILE = "scrape_profile"
    SCRAPE_POSTS = "scrape_posts"


@dataclass
class ActionResult:
    """Result of an action callback."""
    action_type: ActionType
    success: bool
    target_username: Optional[str] = None
    target_url: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None
    timestamp: datetime = field(default_factory=datetime.now)
    logged: bool = False


class ActionCallback:
    """
    Callback interface for action logging.
    
    Automation scripts call these methods to report actions,
    which are then logged to the backend.
    
    Usage:
        # Initialize with account and session
        callback = ActionCallback(
            api_client=client,
            account_id=1,
            session_id=123
        )
        
        # Report actions
        callback.on_follow("someuser", success=True)
        callback.on_like("https://instagram.com/p/xyz", success=True)
        
        # Get summary
        print(callback.get_summary())
    """
    
    def __init__(
        self,
        api_client: InstaApiClient,
        account_id: int,
        session_id: int = None,
        auto_log: bool = True,
        on_error_callback: Callable[[ActionResult], None] = None
    ):
        """
        Initialize action callback.
        
        Args:
            api_client: Backend API client instance
            account_id: Bot account ID
            session_id: Current session ID
            auto_log: Automatically log actions to backend
            on_error_callback: Optional callback for failed actions
        """
        self.api_client = api_client
        self.account_id = account_id
        self.session_id = session_id
        self.auto_log = auto_log
        self.on_error_callback = on_error_callback
        
        # Action history for this session
        self.history: list[ActionResult] = []
        
        # Counters
        self.counts = {action.value: 0 for action in ActionType}
        self.success_count = 0
        self.error_count = 0
    
    def _log_action(self, result: ActionResult) -> bool:
        """Log action to backend."""
        if not self.auto_log:
            return False
        
        try:
            response = self.api_client.log_action(
                account_id=self.account_id,
                session_id=self.session_id,
                action_type=result.action_type.value,
                target_username=result.target_username,
                target_url=result.target_url,
                success=result.success,
                error_message=result.error_message,
                metadata=result.metadata
            )
            
            if response.success:
                result.logged = True
                return True
            else:
                logger.warning(f"Failed to log action: {response.error}")
                return False
                
        except Exception as e:
            logger.error(f"Error logging action: {e}")
            return False
    
    def _record_action(self, result: ActionResult):
        """Record action to history and update counters."""
        self.history.append(result)
        self.counts[result.action_type.value] += 1
        
        if result.success:
            self.success_count += 1
        else:
            self.error_count += 1
            if self.on_error_callback:
                self.on_error_callback(result)
        
        # Log to backend
        self._log_action(result)
    
    # ==================== Action Methods ====================
    
    def on_follow(
        self,
        target_username: str,
        success: bool = True,
        error_message: str = None,
        metadata: Dict = None
    ) -> ActionResult:
        """Record a follow action."""
        result = ActionResult(
            action_type=ActionType.FOLLOW,
            success=success,
            target_username=target_username,
            error_message=error_message,
            metadata=metadata
        )
        self._record_action(result)
        logger.info(f"{'✓' if success else '✗'} Follow: @{target_username}")
        return result
    
    def on_unfollow(
        self,
        target_username: str,
        success: bool = True,
        error_message: str = None,
        metadata: Dict = None
    ) -> ActionResult:
        """Record an unfollow action."""
        result = ActionResult(
            action_type=ActionType.UNFOLLOW,
            success=success,
            target_username=target_username,
            error_message=error_message,
            metadata=metadata
        )
        self._record_action(result)
        logger.info(f"{'✓' if success else '✗'} Unfollow: @{target_username}")
        return result
    
    def on_like(
        self,
        target_url: str,
        success: bool = True,
        error_message: str = None,
        metadata: Dict = None
    ) -> ActionResult:
        """Record a like action."""
        result = ActionResult(
            action_type=ActionType.LIKE,
            success=success,
            target_url=target_url,
            error_message=error_message,
            metadata=metadata
        )
        self._record_action(result)
        logger.info(f"{'✓' if success else '✗'} Like: {target_url[:50]}...")
        return result
    
    def on_unlike(
        self,
        target_url: str,
        success: bool = True,
        error_message: str = None,
        metadata: Dict = None
    ) -> ActionResult:
        """Record an unlike action."""
        result = ActionResult(
            action_type=ActionType.UNLIKE,
            success=success,
            target_url=target_url,
            error_message=error_message,
            metadata=metadata
        )
        self._record_action(result)
        logger.info(f"{'✓' if success else '✗'} Unlike: {target_url[:50]}...")
        return result
    
    def on_comment(
        self,
        target_url: str,
        comment_text: str,
        success: bool = True,
        error_message: str = None,
        metadata: Dict = None
    ) -> ActionResult:
        """Record a comment action."""
        meta = metadata or {}
        meta["comment_text"] = comment_text
        
        result = ActionResult(
            action_type=ActionType.COMMENT,
            success=success,
            target_url=target_url,
            error_message=error_message,
            metadata=meta
        )
        self._record_action(result)
        logger.info(f"{'✓' if success else '✗'} Comment: {comment_text[:30]}...")
        return result
    
    def on_story_view(
        self,
        target_username: str,
        success: bool = True,
        stories_count: int = 1,
        error_message: str = None,
        metadata: Dict = None
    ) -> ActionResult:
        """Record a story view action."""
        meta = metadata or {}
        meta["stories_count"] = stories_count
        
        result = ActionResult(
            action_type=ActionType.VIEW_STORY,
            success=success,
            target_username=target_username,
            error_message=error_message,
            metadata=meta
        )
        self._record_action(result)
        logger.info(f"{'✓' if success else '✗'} View story: @{target_username} ({stories_count} stories)")
        return result
    
    def on_download(
        self,
        target_url: str,
        media_type: str = None,
        file_path: str = None,
        success: bool = True,
        error_message: str = None,
        metadata: Dict = None
    ) -> ActionResult:
        """Record a download action."""
        meta = metadata or {}
        if media_type:
            meta["media_type"] = media_type
        if file_path:
            meta["file_path"] = file_path
        
        result = ActionResult(
            action_type=ActionType.DOWNLOAD,
            success=success,
            target_url=target_url,
            error_message=error_message,
            metadata=meta
        )
        self._record_action(result)
        logger.info(f"{'✓' if success else '✗'} Download: {target_url[:50]}...")
        return result
    
    def on_scrape_profile(
        self,
        target_username: str,
        success: bool = True,
        profile_data: Dict = None,
        error_message: str = None
    ) -> ActionResult:
        """Record a profile scrape action."""
        result = ActionResult(
            action_type=ActionType.SCRAPE_PROFILE,
            success=success,
            target_username=target_username,
            error_message=error_message,
            metadata=profile_data
        )
        self._record_action(result)
        logger.info(f"{'✓' if success else '✗'} Scrape profile: @{target_username}")
        return result
    
    def on_scrape_posts(
        self,
        target_username: str,
        posts_count: int = 0,
        success: bool = True,
        error_message: str = None,
        metadata: Dict = None
    ) -> ActionResult:
        """Record a posts scrape action."""
        meta = metadata or {}
        meta["posts_count"] = posts_count
        
        result = ActionResult(
            action_type=ActionType.SCRAPE_POSTS,
            success=success,
            target_username=target_username,
            error_message=error_message,
            metadata=meta
        )
        self._record_action(result)
        logger.info(f"{'✓' if success else '✗'} Scrape posts: @{target_username} ({posts_count} posts)")
        return result
    
    def on_error(
        self,
        action_type: ActionType,
        error_message: str,
        target_username: str = None,
        target_url: str = None,
        metadata: Dict = None
    ) -> ActionResult:
        """Record a generic error."""
        result = ActionResult(
            action_type=action_type,
            success=False,
            target_username=target_username,
            target_url=target_url,
            error_message=error_message,
            metadata=metadata
        )
        self._record_action(result)
        logger.error(f"✗ Error in {action_type.value}: {error_message}")
        return result
    
    # ==================== Summary Methods ====================
    
    def get_summary(self) -> Dict[str, Any]:
        """Get action summary for this session."""
        return {
            "account_id": self.account_id,
            "session_id": self.session_id,
            "total_actions": len(self.history),
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": (
                self.success_count / len(self.history) * 100
                if self.history else 0
            ),
            "action_counts": self.counts,
        }
    
    def get_history(self) -> list[ActionResult]:
        """Get full action history."""
        return self.history.copy()
    
    def clear_history(self):
        """Clear action history (useful for long-running sessions)."""
        self.history.clear()
