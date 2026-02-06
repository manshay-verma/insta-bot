"""
In-Memory Rate Limiter Implementation

Uses a sliding window algorithm for accurate rate limiting without external dependencies.
"""

import time
from collections import defaultdict
from threading import Lock
from typing import Dict, Optional, List
import logging

from .base import RateLimiter, RateLimitStatus

logger = logging.getLogger(__name__)


class MemoryRateLimiter(RateLimiter):
    """
    Thread-safe in-memory rate limiter using sliding window algorithm.
    
    This implementation:
    - Uses sliding windows for accurate rate limiting
    - Supports per-hour and per-day limits
    - Supports different limits per action type
    - Is thread-safe for concurrent access
    
    Example:
        limiter = MemoryRateLimiter(actions_per_hour=60, actions_per_day=500)
        
        if limiter.can_perform("like"):
            # Do the action
            limiter.record_action("like")
        else:
            status = limiter.get_status("like")
            print(f"Rate limited! Wait {status.reset_seconds:.0f}s")
    """
    
    def __init__(
        self,
        actions_per_hour: int = 60,
        actions_per_day: int = 500,
        per_action_limits: Optional[Dict[str, int]] = None
    ):
        """
        Initialize the rate limiter.
        
        Args:
            actions_per_hour: Maximum actions allowed per hour (global)
            actions_per_day: Maximum actions allowed per day (global)
            per_action_limits: Optional dict of action_type -> hourly limit
        """
        self.actions_per_hour = actions_per_hour
        self.actions_per_day = actions_per_day
        self.per_action_limits = per_action_limits or {}
        
        # Storage: action_type -> list of timestamps
        self._action_timestamps: Dict[str, List[float]] = defaultdict(list)
        
        # Global timestamps (for global limits)
        self._global_timestamps: List[float] = []
        
        # Thread safety
        self._lock = Lock()
        
        logger.info(
            f"MemoryRateLimiter initialized: "
            f"{actions_per_hour}/hour, {actions_per_day}/day"
        )
    
    def _cleanup_old_timestamps(self, timestamps: List[float], window_seconds: float) -> List[float]:
        """Remove timestamps older than the window."""
        cutoff = time.time() - window_seconds
        return [ts for ts in timestamps if ts > cutoff]
    
    def _get_hourly_limit(self, action_type: str) -> int:
        """Get the hourly limit for an action type."""
        return self.per_action_limits.get(action_type, self.actions_per_hour)
    
    def can_perform(self, action_type: str = "default") -> bool:
        """Check if an action can be performed without exceeding limits."""
        with self._lock:
            now = time.time()
            hour_ago = now - 3600
            day_ago = now - 86400
            
            # Clean up old timestamps
            self._global_timestamps = self._cleanup_old_timestamps(
                self._global_timestamps, 86400
            )
            self._action_timestamps[action_type] = self._cleanup_old_timestamps(
                self._action_timestamps[action_type], 3600
            )
            
            # Check hourly limit for this action type
            hourly_limit = self._get_hourly_limit(action_type)
            hourly_count = len(self._action_timestamps[action_type])
            if hourly_count >= hourly_limit:
                logger.debug(f"Rate limit hit for {action_type}: {hourly_count}/{hourly_limit} per hour")
                return False
            
            # Check global hourly limit
            global_hourly = len([ts for ts in self._global_timestamps if ts > hour_ago])
            if global_hourly >= self.actions_per_hour:
                logger.debug(f"Global hourly limit hit: {global_hourly}/{self.actions_per_hour}")
                return False
            
            # Check global daily limit
            global_daily = len(self._global_timestamps)
            if global_daily >= self.actions_per_day:
                logger.debug(f"Global daily limit hit: {global_daily}/{self.actions_per_day}")
                return False
            
            return True
    
    def record_action(self, action_type: str = "default") -> bool:
        """Record that an action was performed."""
        with self._lock:
            if not self.can_perform(action_type):
                return False
            
            now = time.time()
            self._action_timestamps[action_type].append(now)
            self._global_timestamps.append(now)
            
            logger.debug(f"Recorded action: {action_type}")
            return True
    
    def get_status(self, action_type: str = "default") -> RateLimitStatus:
        """Get the current rate limit status for an action type."""
        with self._lock:
            now = time.time()
            hour_ago = now - 3600
            
            # Clean up
            self._action_timestamps[action_type] = self._cleanup_old_timestamps(
                self._action_timestamps[action_type], 3600
            )
            
            hourly_limit = self._get_hourly_limit(action_type)
            hourly_count = len(self._action_timestamps[action_type])
            remaining = max(0, hourly_limit - hourly_count)
            
            # Calculate reset time (when oldest action expires)
            if self._action_timestamps[action_type] and remaining == 0:
                oldest = min(self._action_timestamps[action_type])
                reset_seconds = max(0, (oldest + 3600) - now)
            else:
                reset_seconds = 0.0
            
            return RateLimitStatus(
                allowed=remaining > 0,
                remaining=remaining,
                limit=hourly_limit,
                reset_seconds=reset_seconds,
                action_type=action_type
            )
    
    def get_all_status(self) -> Dict[str, RateLimitStatus]:
        """Get rate limit status for all tracked action types."""
        with self._lock:
            result = {}
            
            # Include all tracked action types
            all_types = set(self._action_timestamps.keys()) | set(self.per_action_limits.keys())
            
            for action_type in all_types:
                result[action_type] = self.get_status(action_type)
            
            # Add global status
            now = time.time()
            hour_ago = now - 3600
            day_ago = now - 86400
            
            self._global_timestamps = self._cleanup_old_timestamps(
                self._global_timestamps, 86400
            )
            
            global_hourly = len([ts for ts in self._global_timestamps if ts > hour_ago])
            global_daily = len(self._global_timestamps)
            
            result["_global_hourly"] = RateLimitStatus(
                allowed=global_hourly < self.actions_per_hour,
                remaining=max(0, self.actions_per_hour - global_hourly),
                limit=self.actions_per_hour,
                reset_seconds=0.0,
                action_type="_global_hourly"
            )
            
            result["_global_daily"] = RateLimitStatus(
                allowed=global_daily < self.actions_per_day,
                remaining=max(0, self.actions_per_day - global_daily),
                limit=self.actions_per_day,
                reset_seconds=0.0,
                action_type="_global_daily"
            )
            
            return result
    
    def reset(self, action_type: Optional[str] = None) -> None:
        """Reset rate limit counters."""
        with self._lock:
            if action_type:
                self._action_timestamps[action_type] = []
                logger.info(f"Reset rate limits for: {action_type}")
            else:
                self._action_timestamps.clear()
                self._global_timestamps.clear()
                logger.info("Reset all rate limits")
    
    def get_summary(self) -> Dict[str, any]:
        """Get a human-readable summary of current usage."""
        with self._lock:
            now = time.time()
            hour_ago = now - 3600
            
            self._global_timestamps = self._cleanup_old_timestamps(
                self._global_timestamps, 86400
            )
            
            global_hourly = len([ts for ts in self._global_timestamps if ts > hour_ago])
            global_daily = len(self._global_timestamps)
            
            return {
                "global": {
                    "hourly": f"{global_hourly}/{self.actions_per_hour}",
                    "daily": f"{global_daily}/{self.actions_per_day}",
                },
                "by_action": {
                    action: f"{len(timestamps)}/{self._get_hourly_limit(action)}/hr"
                    for action, timestamps in self._action_timestamps.items()
                }
            }
