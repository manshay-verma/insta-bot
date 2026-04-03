"""
Safety Adapter

Connects orchestrator with automation/safety/
Provides rate limiting, delay generation, and health tracking.
"""

import logging
import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any

from .base_adapter import BaseAdapter, AdapterType, TaskType, TaskResult

# Add automation to path
automation_path = Path(__file__).parent.parent.parent / "automation"
sys.path.insert(0, str(automation_path))

logger = logging.getLogger(__name__)


class SafetyAdapter(BaseAdapter):
    """
    Adapter for safety module.
    
    Wraps automation/safety/:
    - RateLimiter: Check and enforce action limits
    - DelayGenerator: Get human-like delays
    - HealthTracker: Track account health
    - ActionLogger: Log actions for audit
    
    Supported Tasks:
    - CHECK_RATE_LIMIT
    - GET_DELAY
    - CHECK_HEALTH
    
    Usage:
        adapter = SafetyAdapter(api_client, account_id=1)
        await adapter.initialize()
        
        # Check rate limit before action
        result = await adapter.execute(TaskType.CHECK_RATE_LIMIT, ["follow"])
        if result.data["allowed"]:
            # Proceed with follow...
        
        # Get delay between actions
        delay_result = await adapter.execute(TaskType.GET_DELAY, ["follow"])
        await asyncio.sleep(delay_result.data["delay"])
    """
    
    adapter_type = AdapterType.SAFETY
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rate_limiter = None
        self.delay_generator = None
        self.health_tracker = None
        self.action_logger = None
    
    async def initialize(self) -> bool:
        """Initialize safety components."""
        try:
            from safety import (
                RateLimiter,
                MemoryRateLimiter,
                DelayGenerator,
                HealthTracker,
                ActionLogger,
                SafetyConfig,
            )
            
            # Use memory-based rate limiter by default
            self.rate_limiter = MemoryRateLimiter(account_id=str(self.account_id))
            self.delay_generator = DelayGenerator()
            self.health_tracker = HealthTracker(account_id=str(self.account_id))
            self.action_logger = ActionLogger(account_id=str(self.account_id))
            
            self._initialized = True
            logger.info(f"Safety adapter initialized for account {self.account_id}")
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import safety module: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize safety: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup safety resources."""
        self.rate_limiter = None
        self.delay_generator = None
        self.health_tracker = None
        self.action_logger = None
        self._initialized = False
        logger.info("Safety adapter cleaned up")
    
    def get_supported_tasks(self) -> List[TaskType]:
        """Get supported task types."""
        return [
            TaskType.CHECK_RATE_LIMIT,
            TaskType.GET_DELAY,
            TaskType.CHECK_HEALTH,
        ]
    
    async def execute(
        self,
        task_type: TaskType,
        targets: List[str],
        **kwargs
    ) -> TaskResult:
        """Execute a safety task."""
        if not self._initialized:
            return TaskResult(
                success=False,
                task_type=task_type,
                errors=["Adapter not initialized"]
            )
        
        handlers = {
            TaskType.CHECK_RATE_LIMIT: self._check_rate_limit,
            TaskType.GET_DELAY: self._get_delay,
            TaskType.CHECK_HEALTH: self._check_health,
        }
        
        handler = handlers.get(task_type)
        if not handler:
            return TaskResult(
                success=False,
                task_type=task_type,
                errors=[f"Unsupported task: {task_type}"]
            )
        
        return await handler(targets, **kwargs)
    
    # ==================== Task Handlers ====================
    
    async def _check_rate_limit(self, targets: List[str], **kwargs) -> TaskResult:
        """Check if action is allowed under rate limits."""
        action_type = targets[0] if targets else "follow"
        
        try:
            # Check with local rate limiter
            status = self.rate_limiter.check_limit(action_type)
            
            # Also fetch limits from backend
            response = self.api_client.get_rate_limits(self.account_id)
            backend_limits = response.data if response.success else {}
            
            return TaskResult(
                success=True,
                task_type=TaskType.CHECK_RATE_LIMIT,
                data={
                    "action_type": action_type,
                    "allowed": status.allowed if hasattr(status, 'allowed') else True,
                    "remaining": status.remaining if hasattr(status, 'remaining') else 0,
                    "reset_at": status.reset_at if hasattr(status, 'reset_at') else None,
                    "backend_limits": backend_limits,
                }
            )
        except Exception as e:
            return TaskResult(
                success=False,
                task_type=TaskType.CHECK_RATE_LIMIT,
                errors=[str(e)]
            )
    
    async def _get_delay(self, targets: List[str], **kwargs) -> TaskResult:
        """Get recommended delay for action."""
        action_type = targets[0] if targets else "follow"
        
        try:
            delay = self.delay_generator.get_delay(action_type)
            
            return TaskResult(
                success=True,
                task_type=TaskType.GET_DELAY,
                data={
                    "action_type": action_type,
                    "delay": delay,
                    "unit": "seconds"
                }
            )
        except Exception as e:
            # Fallback to default delay
            import random
            default_delay = random.uniform(15, 45)
            
            return TaskResult(
                success=True,
                task_type=TaskType.GET_DELAY,
                data={
                    "action_type": action_type,
                    "delay": default_delay,
                    "unit": "seconds",
                    "fallback": True
                }
            )
    
    async def _check_health(self, targets: List[str], **kwargs) -> TaskResult:
        """Check account health status."""
        try:
            # Get health from backend
            response = self.api_client.get_account_health(self.account_id)
            
            if response.success:
                health_data = response.data
                
                # Update local health tracker
                if self.health_tracker:
                    self.health_tracker.update(health_data)
                
                return TaskResult(
                    success=True,
                    task_type=TaskType.CHECK_HEALTH,
                    data=health_data
                )
            else:
                return TaskResult(
                    success=False,
                    task_type=TaskType.CHECK_HEALTH,
                    errors=[response.error]
                )
                
        except Exception as e:
            return TaskResult(
                success=False,
                task_type=TaskType.CHECK_HEALTH,
                errors=[str(e)]
            )
    
    # ==================== Utility Methods ====================
    
    async def record_action(self, action_type: str, success: bool = True):
        """Record an action for rate limiting."""
        if self.rate_limiter:
            self.rate_limiter.record_action(action_type)
        
        if self.action_logger:
            self.action_logger.log(action_type, success=success)
    
    async def should_pause(self) -> bool:
        """Check if bot should pause based on health."""
        if not self.health_tracker:
            return False
        
        try:
            response = self.api_client.get_account_health(self.account_id)
            if response.success:
                return not response.data.get("is_healthy", True)
        except:
            pass
        
        return False
    
    async def get_sleep_schedule(self) -> Dict[str, Any]:
        """Get recommended sleep hours."""
        try:
            from safety import SleepSchedule
            schedule = SleepSchedule()
            
            return {
                "should_sleep": schedule.should_sleep(),
                "next_wake": schedule.next_wake_time(),
                "sleep_start": "23:00",
                "sleep_end": "07:00"
            }
        except:
            return {
                "should_sleep": False,
                "fallback": True
            }
