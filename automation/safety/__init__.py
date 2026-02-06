"""
Safety Module

Provides rate limiting, human behavior simulation, and risk management
for Instagram automation to avoid detection and bans.
"""

from .config import SafetyConfig, RateLimitConfig, BehaviorConfig, RiskConfig
from .rate_limiter import RateLimiter, RateLimitStatus, MemoryRateLimiter, RedisRateLimiter
from .behavior import DelayGenerator, SleepSchedule, ActionSequencer, WarmupManager
from .risk import HealthTracker, SignalDetector, AutoPause, HealthLevel
from .logging import ActionLogger

__all__ = [
    # Config
    "SafetyConfig",
    "RateLimitConfig",
    "BehaviorConfig",
    "RiskConfig",
    # Rate Limiting
    "RateLimiter",
    "RateLimitStatus",
    "MemoryRateLimiter",
    "RedisRateLimiter",
    # Behavior
    "DelayGenerator",
    "SleepSchedule",
    "ActionSequencer",
    "WarmupManager",
    # Risk Management
    "HealthTracker",
    "HealthLevel",
    "SignalDetector",
    "AutoPause",
    # Logging
    "ActionLogger",
]

__version__ = "1.0.0"

