"""
Redis-Backed Rate Limiter

Uses Redis for distributed rate limiting across multiple instances.
Implements the same interface as MemoryRateLimiter.
"""

import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed. Install with: pip install redis")

from .base import RateLimiter, RateLimitStatus


class RedisRateLimiter(RateLimiter):
    """
    Redis-backed rate limiter for distributed environments.
    
    Uses Redis sorted sets with sliding window algorithm for accurate
    rate limiting across multiple instances/processes.
    
    Features:
    - Distributed rate limiting across instances
    - Automatic key expiration
    - Per-action type limits
    - Thread/process-safe
    
    Example:
        limiter = RedisRateLimiter(
            redis_url="redis://localhost:6379/0",
            actions_per_hour=60,
            actions_per_day=500
        )
        
        if limiter.can_perform("like"):
            # Do the action
            limiter.record_action("like")
        else:
            status = limiter.get_status("like")
            print(f"Rate limited! Wait {status.reset_seconds:.0f}s")
    
    Requires:
        pip install redis
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        actions_per_hour: int = 60,
        actions_per_day: int = 500,
        per_action_limits: Optional[Dict[str, int]] = None,
        key_prefix: str = "instabot:ratelimit",
        account_id: str = "default"
    ):
        """
        Initialize the Redis rate limiter.
        
        Args:
            redis_url: Redis connection URL
            actions_per_hour: Maximum actions per hour (global)
            actions_per_day: Maximum actions per day (global)
            per_action_limits: Dict of action_type -> hourly limit
            key_prefix: Prefix for Redis keys
            account_id: Account identifier for key namespacing
        """
        if not REDIS_AVAILABLE:
            raise ImportError("Redis package not installed. Run: pip install redis")
        
        self.redis_url = redis_url
        self.actions_per_hour = actions_per_hour
        self.actions_per_day = actions_per_day
        self.per_action_limits = per_action_limits or {}
        self.key_prefix = key_prefix
        self.account_id = account_id
        
        # Connect to Redis
        self._redis = redis.from_url(redis_url, decode_responses=True)
        
        # Test connection
        try:
            self._redis.ping()
            logger.info(f"RedisRateLimiter connected: {redis_url}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def _get_key(self, action_type: str, window: str = "hour") -> str:
        """Generate Redis key for action type and window."""
        return f"{self.key_prefix}:{self.account_id}:{action_type}:{window}"
    
    def _get_global_key(self, window: str = "hour") -> str:
        """Generate Redis key for global limits."""
        return f"{self.key_prefix}:{self.account_id}:_global:{window}"
    
    def _get_hourly_limit(self, action_type: str) -> int:
        """Get hourly limit for an action type."""
        return self.per_action_limits.get(action_type, self.actions_per_hour)
    
    def _cleanup_window(self, key: str, window_seconds: float) -> None:
        """Remove timestamps older than the window."""
        cutoff = time.time() - window_seconds
        self._redis.zremrangebyscore(key, "-inf", cutoff)
    
    def _count_in_window(self, key: str, window_seconds: float) -> int:
        """Count actions within the time window."""
        cutoff = time.time() - window_seconds
        return self._redis.zcount(key, cutoff, "+inf")
    
    def can_perform(self, action_type: str = "default") -> bool:
        """Check if an action can be performed without exceeding limits."""
        now = time.time()
        hour_ago = now - 3600
        day_ago = now - 86400
        
        # Get keys
        action_key = self._get_key(action_type, "hour")
        global_hour_key = self._get_global_key("hour")
        global_day_key = self._get_global_key("day")
        
        # Cleanup old entries
        self._cleanup_window(action_key, 3600)
        self._cleanup_window(global_hour_key, 3600)
        self._cleanup_window(global_day_key, 86400)
        
        # Check action-specific hourly limit
        hourly_limit = self._get_hourly_limit(action_type)
        hourly_count = self._count_in_window(action_key, 3600)
        if hourly_count >= hourly_limit:
            logger.debug(f"Rate limit hit for {action_type}: {hourly_count}/{hourly_limit}")
            return False
        
        # Check global hourly limit
        global_hourly = self._count_in_window(global_hour_key, 3600)
        if global_hourly >= self.actions_per_hour:
            logger.debug(f"Global hourly limit hit: {global_hourly}/{self.actions_per_hour}")
            return False
        
        # Check global daily limit
        global_daily = self._count_in_window(global_day_key, 86400)
        if global_daily >= self.actions_per_day:
            logger.debug(f"Global daily limit hit: {global_daily}/{self.actions_per_day}")
            return False
        
        return True
    
    def record_action(self, action_type: str = "default") -> bool:
        """Record that an action was performed."""
        if not self.can_perform(action_type):
            return False
        
        now = time.time()
        unique_id = f"{now}:{id(self)}"  # Unique timestamp ID
        
        # Get keys
        action_key = self._get_key(action_type, "hour")
        global_hour_key = self._get_global_key("hour")
        global_day_key = self._get_global_key("day")
        
        # Use pipeline for atomic operations
        pipe = self._redis.pipeline()
        
        # Add to action-specific set
        pipe.zadd(action_key, {unique_id: now})
        pipe.expire(action_key, 3700)  # Slightly more than 1 hour
        
        # Add to global hourly set
        pipe.zadd(global_hour_key, {unique_id: now})
        pipe.expire(global_hour_key, 3700)
        
        # Add to global daily set
        pipe.zadd(global_day_key, {unique_id: now})
        pipe.expire(global_day_key, 86500)  # Slightly more than 1 day
        
        pipe.execute()
        
        logger.debug(f"Recorded action: {action_type}")
        return True
    
    def get_status(self, action_type: str = "default") -> RateLimitStatus:
        """Get the current rate limit status for an action type."""
        action_key = self._get_key(action_type, "hour")
        
        # Cleanup old entries
        self._cleanup_window(action_key, 3600)
        
        hourly_limit = self._get_hourly_limit(action_type)
        hourly_count = self._count_in_window(action_key, 3600)
        remaining = max(0, hourly_limit - hourly_count)
        
        # Calculate reset time
        reset_seconds = 0.0
        if remaining == 0:
            # Get oldest timestamp in window
            oldest = self._redis.zrange(action_key, 0, 0, withscores=True)
            if oldest:
                oldest_time = oldest[0][1]
                reset_seconds = max(0, (oldest_time + 3600) - time.time())
        
        return RateLimitStatus(
            allowed=remaining > 0,
            remaining=remaining,
            limit=hourly_limit,
            reset_seconds=reset_seconds,
            action_type=action_type
        )
    
    def get_all_status(self) -> Dict[str, RateLimitStatus]:
        """Get rate limit status for all tracked action types."""
        result = {}
        
        # Get all action types from keys
        pattern = f"{self.key_prefix}:{self.account_id}:*:hour"
        keys = self._redis.keys(pattern)
        
        action_types = set()
        for key in keys:
            parts = key.split(":")
            if len(parts) >= 4:
                action_types.add(parts[-2])
        
        # Add configured action types
        action_types.update(self.per_action_limits.keys())
        action_types.discard("_global")
        
        for action_type in action_types:
            result[action_type] = self.get_status(action_type)
        
        # Add global status
        global_hour_key = self._get_global_key("hour")
        global_day_key = self._get_global_key("day")
        
        self._cleanup_window(global_hour_key, 3600)
        self._cleanup_window(global_day_key, 86400)
        
        global_hourly = self._count_in_window(global_hour_key, 3600)
        global_daily = self._count_in_window(global_day_key, 86400)
        
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
        if action_type:
            # Reset specific action type
            key = self._get_key(action_type, "hour")
            self._redis.delete(key)
            logger.info(f"Reset rate limits for: {action_type}")
        else:
            # Reset all keys for this account
            pattern = f"{self.key_prefix}:{self.account_id}:*"
            keys = self._redis.keys(pattern)
            if keys:
                self._redis.delete(*keys)
            logger.info("Reset all rate limits")
    
    def get_summary(self) -> Dict:
        """Get a human-readable summary of current usage."""
        global_hour_key = self._get_global_key("hour")
        global_day_key = self._get_global_key("day")
        
        self._cleanup_window(global_hour_key, 3600)
        self._cleanup_window(global_day_key, 86400)
        
        global_hourly = self._count_in_window(global_hour_key, 3600)
        global_daily = self._count_in_window(global_day_key, 86400)
        
        # Get per-action counts
        by_action = {}
        pattern = f"{self.key_prefix}:{self.account_id}:*:hour"
        keys = self._redis.keys(pattern)
        
        for key in keys:
            parts = key.split(":")
            if len(parts) >= 4:
                action_type = parts[-2]
                if action_type != "_global":
                    count = self._count_in_window(key, 3600)
                    limit = self._get_hourly_limit(action_type)
                    by_action[action_type] = f"{count}/{limit}/hr"
        
        return {
            "global": {
                "hourly": f"{global_hourly}/{self.actions_per_hour}",
                "daily": f"{global_daily}/{self.actions_per_day}",
            },
            "by_action": by_action,
            "redis_connected": self._redis.ping() if self._redis else False
        }
    
    def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            self._redis.close()
            logger.info("Redis connection closed")
