"""
Random Delay Generator

Generates human-like random delays between actions to avoid detection.
Uses various distributions to simulate natural human behavior.
"""

import random
import time
import logging
from typing import Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DelayConfig:
    """Configuration for delay generation."""
    min_delay: float = 15.0
    max_delay: float = 45.0
    # Add jitter for more natural variation
    jitter_percent: float = 0.2
    # Use normal distribution instead of uniform
    use_normal_distribution: bool = True


class DelayGenerator:
    """
    Generates random delays between actions to simulate human behavior.
    
    Features:
    - Configurable min/max delays
    - Normal distribution for more natural patterns
    - Jitter for additional randomness
    - Action-specific delay multipliers
    
    Example:
        generator = DelayGenerator(min_delay=15, max_delay=45)
        
        # Wait before performing action
        await generator.wait()
        
        # Or get delay value
        delay = generator.get_delay()
        print(f"Waiting {delay:.1f} seconds")
    """
    
    def __init__(
        self,
        min_delay: float = 15.0,
        max_delay: float = 45.0,
        jitter_percent: float = 0.2,
        use_normal_distribution: bool = True
    ):
        """
        Initialize the delay generator.
        
        Args:
            min_delay: Minimum delay in seconds (default: 15)
            max_delay: Maximum delay in seconds (default: 45)
            jitter_percent: Additional random variation (0.0 to 1.0)
            use_normal_distribution: Use normal distribution for more natural delays
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.jitter_percent = jitter_percent
        self.use_normal_distribution = use_normal_distribution
        
        # Action-specific multipliers
        self._action_multipliers = {
            "like": 1.0,
            "follow": 1.5,      # Longer delay for follows
            "unfollow": 1.5,
            "comment": 2.0,     # Longest delay for comments
            "dm": 2.5,
            "story_view": 0.5,  # Shorter delay for story views
        }
        
        logger.info(
            f"DelayGenerator initialized: {min_delay}-{max_delay}s "
            f"(normal={use_normal_distribution})"
        )
    
    def get_delay(self, action_type: Optional[str] = None) -> float:
        """
        Generate a random delay value.
        
        Args:
            action_type: Optional action type for specific delay multiplier
            
        Returns:
            Delay in seconds
        """
        if self.use_normal_distribution:
            # Use normal distribution centered at midpoint
            mean = (self.min_delay + self.max_delay) / 2
            std = (self.max_delay - self.min_delay) / 4  # ~95% within range
            delay = random.gauss(mean, std)
            # Clamp to range
            delay = max(self.min_delay, min(self.max_delay, delay))
        else:
            # Simple uniform distribution
            delay = random.uniform(self.min_delay, self.max_delay)
        
        # Apply jitter
        if self.jitter_percent > 0:
            jitter = delay * random.uniform(-self.jitter_percent, self.jitter_percent)
            delay += jitter
            # Ensure still within reasonable bounds
            delay = max(self.min_delay * 0.8, delay)
        
        # Apply action-specific multiplier
        if action_type and action_type in self._action_multipliers:
            delay *= self._action_multipliers[action_type]
        
        logger.debug(f"Generated delay: {delay:.2f}s (action={action_type})")
        return delay
    
    def set_action_multiplier(self, action_type: str, multiplier: float) -> None:
        """
        Set a custom multiplier for an action type.
        
        Args:
            action_type: The action type (e.g., "like", "follow")
            multiplier: Delay multiplier (1.0 = normal, 2.0 = double delay)
        """
        self._action_multipliers[action_type] = multiplier
        logger.debug(f"Set multiplier for {action_type}: {multiplier}")
    
    def wait(self, action_type: Optional[str] = None) -> float:
        """
        Block execution for a random delay (synchronous).
        
        Args:
            action_type: Optional action type for specific delay
            
        Returns:
            Actual delay waited
        """
        delay = self.get_delay(action_type)
        logger.info(f"Waiting {delay:.1f}s before {action_type or 'action'}...")
        time.sleep(delay)
        return delay
    
    async def async_wait(self, action_type: Optional[str] = None) -> float:
        """
        Async wait for a random delay.
        
        Args:
            action_type: Optional action type for specific delay
            
        Returns:
            Actual delay waited
        """
        import asyncio
        delay = self.get_delay(action_type)
        logger.info(f"Waiting {delay:.1f}s before {action_type or 'action'}...")
        await asyncio.sleep(delay)
        return delay


# Convenience function
def get_random_delay(min_delay: float = 15.0, max_delay: float = 45.0) -> float:
    """
    Quick function to get a random delay.
    
    Args:
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
        
    Returns:
        Random delay in seconds
    """
    return random.uniform(min_delay, max_delay)
