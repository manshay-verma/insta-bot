"""
Account Health Score Tracker

Tracks account health based on action success rates and other metrics.
Provides early warning when account might be at risk.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import json
import os

logger = logging.getLogger(__name__)


class HealthLevel(Enum):
    """Health level indicators."""
    EXCELLENT = "excellent"   # 90-100%
    GOOD = "good"             # 70-90%
    WARNING = "warning"       # 50-70%
    CRITICAL = "critical"     # Below 50%
    UNKNOWN = "unknown"       # Not enough data


@dataclass
class ActionResult:
    """Result of a single action."""
    action_type: str
    success: bool
    timestamp: datetime
    error_code: Optional[str] = None
    message: Optional[str] = None


@dataclass
class HealthStatus:
    """Current health status for an account."""
    account_id: str
    level: HealthLevel
    score: float  # 0.0 to 1.0
    success_rate: float
    total_actions: int
    successful_actions: int
    failed_actions: int
    recent_failures: int  # Failures in last hour
    last_updated: datetime
    
    @property
    def score_percent(self) -> str:
        """Get score as percentage string."""
        return f"{self.score * 100:.1f}%"
    
    @property
    def is_healthy(self) -> bool:
        """Check if account is in good health."""
        return self.level in (HealthLevel.EXCELLENT, HealthLevel.GOOD)


class HealthTracker:
    """
    Tracks account health based on action success rates.
    
    Features:
    - Rolling window for success rate calculation
    - Multiple health levels (excellent, good, warning, critical)
    - Per-action type tracking
    - History persistence
    
    Example:
        tracker = HealthTracker()
        
        # Record action results
        tracker.record_success("account_123", "like")
        tracker.record_failure("account_123", "follow", error_code="rate_limited")
        
        # Get health status
        status = tracker.get_health("account_123")
        if status.level == HealthLevel.WARNING:
            print("Account needs attention!")
    """
    
    def __init__(
        self,
        window_hours: int = 24,
        excellent_threshold: float = 0.9,
        good_threshold: float = 0.7,
        warning_threshold: float = 0.5,
        state_file: Optional[str] = None,
        max_history: int = 1000
    ):
        """
        Initialize the health tracker.
        
        Args:
            window_hours: Time window for calculating health (default: 24 hours)
            excellent_threshold: Score above this is excellent (default: 0.9)
            good_threshold: Score above this is good (default: 0.7)
            warning_threshold: Score above this is warning (default: 0.5)
            state_file: Optional file to persist state
            max_history: Maximum action history to keep
        """
        self.window_hours = window_hours
        self.excellent_threshold = excellent_threshold
        self.good_threshold = good_threshold
        self.warning_threshold = warning_threshold
        self.state_file = state_file
        self.max_history = max_history
        
        # Per-account action history
        self._history: Dict[str, deque] = {}
        
        # Load existing state
        if state_file and os.path.exists(state_file):
            self._load_state()
        
        logger.info(
            f"HealthTracker initialized: "
            f"window={window_hours}h, thresholds={excellent_threshold}/{good_threshold}/{warning_threshold}"
        )
    
    def record_success(
        self,
        account_id: str,
        action_type: str,
        message: Optional[str] = None
    ) -> None:
        """
        Record a successful action.
        
        Args:
            account_id: Account identifier
            action_type: Type of action performed
            message: Optional success message
        """
        result = ActionResult(
            action_type=action_type,
            success=True,
            timestamp=datetime.now(),
            message=message
        )
        self._add_result(account_id, result)
        logger.debug(f"Recorded success for {account_id}: {action_type}")
    
    def record_failure(
        self,
        account_id: str,
        action_type: str,
        error_code: Optional[str] = None,
        message: Optional[str] = None
    ) -> None:
        """
        Record a failed action.
        
        Args:
            account_id: Account identifier
            action_type: Type of action that failed
            error_code: Optional error code (e.g., "rate_limited", "blocked")
            message: Optional error message
        """
        result = ActionResult(
            action_type=action_type,
            success=False,
            timestamp=datetime.now(),
            error_code=error_code,
            message=message
        )
        self._add_result(account_id, result)
        logger.warning(f"Recorded failure for {account_id}: {action_type} ({error_code})")
    
    def record_result(
        self,
        account_id: str,
        action_type: str,
        success: bool,
        error_code: Optional[str] = None,
        message: Optional[str] = None
    ) -> None:
        """
        Record an action result.
        
        Args:
            account_id: Account identifier
            action_type: Type of action
            success: Whether the action succeeded
            error_code: Optional error code if failed
            message: Optional message
        """
        if success:
            self.record_success(account_id, action_type, message)
        else:
            self.record_failure(account_id, action_type, error_code, message)
    
    def _add_result(self, account_id: str, result: ActionResult) -> None:
        """Add a result to the history."""
        if account_id not in self._history:
            self._history[account_id] = deque(maxlen=self.max_history)
        
        self._history[account_id].append(result)
        self._cleanup_old_results(account_id)
        self._save_state()
    
    def _cleanup_old_results(self, account_id: str) -> None:
        """Remove results older than the window."""
        if account_id not in self._history:
            return
        
        cutoff = datetime.now() - timedelta(hours=self.window_hours * 2)
        history = self._history[account_id]
        
        # Remove old entries from the front
        while history and history[0].timestamp < cutoff:
            history.popleft()
    
    def get_health(self, account_id: str) -> HealthStatus:
        """
        Get the current health status for an account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            HealthStatus with current health metrics
        """
        if account_id not in self._history or not self._history[account_id]:
            return HealthStatus(
                account_id=account_id,
                level=HealthLevel.UNKNOWN,
                score=1.0,
                success_rate=1.0,
                total_actions=0,
                successful_actions=0,
                failed_actions=0,
                recent_failures=0,
                last_updated=datetime.now()
            )
        
        now = datetime.now()
        window_start = now - timedelta(hours=self.window_hours)
        hour_ago = now - timedelta(hours=1)
        
        history = self._history[account_id]
        
        # Filter to window
        window_results = [r for r in history if r.timestamp >= window_start]
        
        if not window_results:
            return HealthStatus(
                account_id=account_id,
                level=HealthLevel.UNKNOWN,
                score=1.0,
                success_rate=1.0,
                total_actions=0,
                successful_actions=0,
                failed_actions=0,
                recent_failures=0,
                last_updated=now
            )
        
        # Calculate metrics
        total = len(window_results)
        successful = sum(1 for r in window_results if r.success)
        failed = total - successful
        recent_failures = sum(
            1 for r in window_results 
            if not r.success and r.timestamp >= hour_ago
        )
        
        success_rate = successful / total if total > 0 else 1.0
        
        # Calculate weighted score (recent failures weighted more heavily)
        recent_weight = recent_failures * 0.1  # Each recent failure reduces score by 10%
        score = max(0.0, success_rate - recent_weight)
        
        # Determine health level
        if score >= self.excellent_threshold:
            level = HealthLevel.EXCELLENT
        elif score >= self.good_threshold:
            level = HealthLevel.GOOD
        elif score >= self.warning_threshold:
            level = HealthLevel.WARNING
        else:
            level = HealthLevel.CRITICAL
        
        return HealthStatus(
            account_id=account_id,
            level=level,
            score=score,
            success_rate=success_rate,
            total_actions=total,
            successful_actions=successful,
            failed_actions=failed,
            recent_failures=recent_failures,
            last_updated=now
        )
    
    def get_failure_trend(self, account_id: str) -> Dict:
        """
        Get failure trend analysis for an account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            Dictionary with trend analysis
        """
        if account_id not in self._history:
            return {"trend": "unknown", "data": []}
        
        now = datetime.now()
        history = self._history[account_id]
        
        # Group by hour for last 24 hours
        hourly_data = {}
        for i in range(24):
            hour_start = now - timedelta(hours=i+1)
            hour_end = now - timedelta(hours=i)
            
            hour_results = [
                r for r in history 
                if hour_start <= r.timestamp < hour_end
            ]
            
            total = len(hour_results)
            failures = sum(1 for r in hour_results if not r.success)
            
            hourly_data[i] = {
                "total": total,
                "failures": failures,
                "rate": failures / total if total > 0 else 0.0
            }
        
        # Determine trend
        recent_rate = sum(hourly_data[i]["rate"] for i in range(6)) / 6  # Last 6 hours
        older_rate = sum(hourly_data[i]["rate"] for i in range(18, 24)) / 6  # 18-24 hours ago
        
        if recent_rate > older_rate + 0.1:
            trend = "worsening"
        elif recent_rate < older_rate - 0.1:
            trend = "improving"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "recent_failure_rate": recent_rate,
            "older_failure_rate": older_rate,
            "hourly_data": hourly_data
        }
    
    def get_error_summary(self, account_id: str) -> Dict[str, int]:
        """
        Get summary of error codes for an account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            Dictionary of error_code -> count
        """
        if account_id not in self._history:
            return {}
        
        errors = {}
        for result in self._history[account_id]:
            if not result.success and result.error_code:
                errors[result.error_code] = errors.get(result.error_code, 0) + 1
        
        return errors
    
    def reset(self, account_id: Optional[str] = None) -> None:
        """
        Reset health history.
        
        Args:
            account_id: If provided, reset only this account. Otherwise reset all.
        """
        if account_id:
            if account_id in self._history:
                self._history[account_id].clear()
                logger.info(f"Reset health history for: {account_id}")
        else:
            self._history.clear()
            logger.info("Reset all health history")
        
        self._save_state()
    
    def _save_state(self) -> None:
        """Save state to file if configured."""
        if not self.state_file:
            return
        
        try:
            data = {}
            for account_id, history in self._history.items():
                data[account_id] = [
                    {
                        "action_type": r.action_type,
                        "success": r.success,
                        "timestamp": r.timestamp.isoformat(),
                        "error_code": r.error_code,
                        "message": r.message
                    }
                    for r in history
                ]
            
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save health state: {e}")
    
    def _load_state(self) -> None:
        """Load state from file if it exists."""
        if not self.state_file or not os.path.exists(self.state_file):
            return
        
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            
            for account_id, history_data in data.items():
                self._history[account_id] = deque(maxlen=self.max_history)
                for item in history_data:
                    result = ActionResult(
                        action_type=item["action_type"],
                        success=item["success"],
                        timestamp=datetime.fromisoformat(item["timestamp"]),
                        error_code=item.get("error_code"),
                        message=item.get("message")
                    )
                    self._history[account_id].append(result)
            
            logger.info(f"Loaded health history for {len(self._history)} accounts")
        except Exception as e:
            logger.error(f"Failed to load health state: {e}")
