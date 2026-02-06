"""
Unit Tests for Rate Limiter Module
"""

import unittest
import time
from unittest.mock import patch

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from automation.safety.rate_limiter import MemoryRateLimiter, RateLimiter
from automation.safety.rate_limiter.base import RateLimitStatus


class TestMemoryRateLimiter(unittest.TestCase):
    """Tests for MemoryRateLimiter."""
    
    def test_init_defaults(self):
        """Test initialization with default values."""
        limiter = MemoryRateLimiter()
        self.assertEqual(limiter.actions_per_hour, 60)
        self.assertEqual(limiter.actions_per_day, 500)
    
    def test_init_custom_limits(self):
        """Test initialization with custom limits."""
        limiter = MemoryRateLimiter(actions_per_hour=100, actions_per_day=1000)
        self.assertEqual(limiter.actions_per_hour, 100)
        self.assertEqual(limiter.actions_per_day, 1000)
    
    def test_can_perform_under_limit(self):
        """Test that actions are allowed when under the limit."""
        limiter = MemoryRateLimiter(actions_per_hour=10)
        self.assertTrue(limiter.can_perform("like"))
    
    def test_record_action(self):
        """Test recording an action."""
        limiter = MemoryRateLimiter(actions_per_hour=10)
        result = limiter.record_action("like")
        self.assertTrue(result)
    
    def test_hourly_limit_enforced(self):
        """Test that hourly limit is enforced."""
        limiter = MemoryRateLimiter(actions_per_hour=3, actions_per_day=100)
        
        # Record 3 actions (at limit)
        for i in range(3):
            self.assertTrue(limiter.record_action("like"), f"Action {i+1} should succeed")
        
        # 4th action should fail
        self.assertFalse(limiter.can_perform("like"))
        self.assertFalse(limiter.record_action("like"))
    
    def test_per_action_type_limits(self):
        """Test per-action type limits."""
        limiter = MemoryRateLimiter(
            actions_per_hour=100,
            per_action_limits={"like": 2, "follow": 1}
        )
        
        # Like limit is 2
        self.assertTrue(limiter.record_action("like"))
        self.assertTrue(limiter.record_action("like"))
        self.assertFalse(limiter.can_perform("like"))
        
        # Follow limit is 1
        self.assertTrue(limiter.record_action("follow"))
        self.assertFalse(limiter.can_perform("follow"))
        
        # Other actions use global limit (100)
        self.assertTrue(limiter.can_perform("comment"))
    
    def test_get_status(self):
        """Test getting rate limit status."""
        limiter = MemoryRateLimiter(actions_per_hour=10)
        limiter.record_action("like")
        limiter.record_action("like")
        
        status = limiter.get_status("like")
        
        self.assertIsInstance(status, RateLimitStatus)
        self.assertEqual(status.remaining, 8)
        self.assertEqual(status.limit, 10)
        self.assertTrue(status.allowed)
        self.assertEqual(status.action_type, "like")
    
    def test_get_status_at_limit(self):
        """Test status when at limit."""
        limiter = MemoryRateLimiter(actions_per_hour=2)
        limiter.record_action("like")
        limiter.record_action("like")
        
        status = limiter.get_status("like")
        
        self.assertFalse(status.allowed)
        self.assertEqual(status.remaining, 0)
    
    def test_reset_specific_action(self):
        """Test resetting a specific action type."""
        limiter = MemoryRateLimiter(actions_per_hour=2)
        limiter.record_action("like")
        limiter.record_action("follow")
        
        limiter.reset("like")
        
        status_like = limiter.get_status("like")
        status_follow = limiter.get_status("follow")
        
        self.assertEqual(status_like.remaining, 2)  # Reset
        self.assertEqual(status_follow.remaining, 1)  # Not reset
    
    def test_reset_all(self):
        """Test resetting all action types."""
        limiter = MemoryRateLimiter(actions_per_hour=5)
        limiter.record_action("like")
        limiter.record_action("follow")
        
        limiter.reset()
        
        status = limiter.get_all_status()
        self.assertEqual(status["_global_hourly"].remaining, 5)
        self.assertEqual(status["_global_daily"].remaining, 500)
    
    def test_check_and_record(self):
        """Test atomic check and record."""
        limiter = MemoryRateLimiter(actions_per_hour=2)
        
        self.assertTrue(limiter.check_and_record("like"))
        self.assertTrue(limiter.check_and_record("like"))
        self.assertFalse(limiter.check_and_record("like"))
    
    def test_usage_percent(self):
        """Test usage percentage calculation."""
        status = RateLimitStatus(
            allowed=True,
            remaining=3,
            limit=10,
            reset_seconds=0,
            action_type="test"
        )
        self.assertEqual(status.usage_percent, 70.0)
    
    def test_get_summary(self):
        """Test human-readable summary."""
        limiter = MemoryRateLimiter(actions_per_hour=60, actions_per_day=500)
        limiter.record_action("like")
        limiter.record_action("like")
        limiter.record_action("follow")
        
        summary = limiter.get_summary()
        
        self.assertIn("global", summary)
        self.assertIn("by_action", summary)
        self.assertEqual(summary["global"]["hourly"], "3/60")
        self.assertEqual(summary["global"]["daily"], "3/500")


class TestRateLimiterInterface(unittest.TestCase):
    """Test that MemoryRateLimiter implements the interface correctly."""
    
    def test_is_subclass(self):
        """Test that MemoryRateLimiter is a RateLimiter."""
        self.assertTrue(issubclass(MemoryRateLimiter, RateLimiter))
    
    def test_has_all_methods(self):
        """Test that all abstract methods are implemented."""
        limiter = MemoryRateLimiter()
        
        # These should not raise NotImplementedError
        limiter.can_perform("test")
        limiter.record_action("test")
        limiter.get_status("test")
        limiter.get_all_status()
        limiter.reset()


if __name__ == '__main__':
    unittest.main()
