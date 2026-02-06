"""
Abstract Base Class for Rate Limiters

Defines the interface that all rate limiter implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class RateLimitStatus:
    """Status of a rate limit check."""
    
    allowed: bool
    remaining: int
    limit: int
    reset_seconds: float
    action_type: str
    
    @property
    def usage_percent(self) -> float:
        """Return usage as a percentage."""
        if self.limit == 0:
            return 0.0
        return ((self.limit - self.remaining) / self.limit) * 100


class RateLimiter(ABC):
    """
    Abstract base class for rate limiters.
    
    All rate limiter implementations (memory, Redis, etc.) must implement this interface.
    """
    
    @abstractmethod
    def can_perform(self, action_type: str = "default") -> bool:
        """
        Check if an action can be performed without exceeding limits.
        
        Args:
            action_type: Type of action (e.g., "like", "follow", "comment")
            
        Returns:
            True if action is allowed, False if rate limited
        """
        pass
    
    @abstractmethod
    def record_action(self, action_type: str = "default") -> bool:
        """
        Record that an action was performed.
        
        Args:
            action_type: Type of action performed
            
        Returns:
            True if recorded successfully, False if limit exceeded
        """
        pass
    
    @abstractmethod
    def get_status(self, action_type: str = "default") -> RateLimitStatus:
        """
        Get the current rate limit status for an action type.
        
        Args:
            action_type: Type of action to check
            
        Returns:
            RateLimitStatus with remaining, limit, and reset info
        """
        pass
    
    @abstractmethod
    def get_all_status(self) -> Dict[str, RateLimitStatus]:
        """
        Get rate limit status for all tracked action types.
        
        Returns:
            Dictionary mapping action_type to RateLimitStatus
        """
        pass
    
    @abstractmethod
    def reset(self, action_type: Optional[str] = None) -> None:
        """
        Reset rate limit counters.
        
        Args:
            action_type: If provided, reset only this action type.
                        If None, reset all counters.
        """
        pass
    
    def check_and_record(self, action_type: str = "default") -> bool:
        """
        Convenience method: check if allowed AND record if so.
        
        This is atomic in most implementations.
        
        Args:
            action_type: Type of action to perform
            
        Returns:
            True if action was allowed and recorded, False if rate limited
        """
        if self.can_perform(action_type):
            return self.record_action(action_type)
        return False
