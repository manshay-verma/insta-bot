"""
Safety Module Configuration

Centralized configuration with sensible defaults for all safety features.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    
    # Global limits
    actions_per_hour: int = 60
    actions_per_day: int = 500
    
    # Per-action type limits (actions per hour)
    per_action_limits: Dict[str, int] = field(default_factory=lambda: {
        "like": 60,
        "follow": 30,
        "unfollow": 30,
        "comment": 20,
        "dm": 15,
        "story_view": 100,
    })


@dataclass
class BehaviorConfig:
    """Configuration for human behavior simulation."""
    
    # Random delays (seconds)
    min_delay: float = 15.0
    max_delay: float = 45.0
    
    # Sleep hours (24-hour format, local time)
    sleep_start_hour: int = 23  # 11 PM
    sleep_end_hour: int = 7     # 7 AM
    
    # Warmup settings (for new accounts)
    warmup_days: int = 7
    warmup_multiplier: float = 0.3  # Start at 30% of normal limits


@dataclass
class RiskConfig:
    """Configuration for risk management."""
    
    # Health thresholds
    warning_threshold: float = 0.7   # 70% success rate triggers warning
    critical_threshold: float = 0.5  # 50% success rate triggers pause
    
    # Auto-pause settings
    pause_on_warning: bool = False
    pause_on_critical: bool = True
    pause_duration_minutes: int = 60


@dataclass
class SafetyConfig:
    """
    Main configuration class for the Safety module.
    
    Usage:
        config = SafetyConfig()
        config.rate_limits.actions_per_hour = 80
        
        # Or with custom sub-configs
        config = SafetyConfig(
            rate_limits=RateLimitConfig(actions_per_hour=100),
            behavior=BehaviorConfig(min_delay=20.0)
        )
    """
    
    rate_limits: RateLimitConfig = field(default_factory=RateLimitConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    
    # Optional Redis connection for distributed rate limiting
    redis_url: Optional[str] = None
    
    # Logging
    enable_logging: bool = True
    log_level: str = "INFO"
