"""
Auto-Pause Controller

Automatically pauses actions when risk thresholds are exceeded.
Integrates with HealthTracker and SignalDetector to make pause decisions.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass
from enum import Enum
import threading
import time

logger = logging.getLogger(__name__)


class PauseReason(Enum):
    """Reasons for pausing actions."""
    RATE_LIMIT = "rate_limit"
    ACTION_BLOCK = "action_block"
    LOW_HEALTH_SCORE = "low_health_score"
    CRITICAL_SIGNAL = "critical_signal"
    MANUAL = "manual"
    SLEEP_HOURS = "sleep_hours"
    WARMUP_LIMIT = "warmup_limit"
    UNKNOWN = "unknown"


@dataclass
class PauseState:
    """Current pause state for an account."""
    account_id: str
    is_paused: bool
    reason: Optional[PauseReason]
    paused_at: Optional[datetime]
    resume_at: Optional[datetime]
    pause_count: int  # Total pauses
    
    @property
    def time_remaining(self) -> float:
        """Seconds until resume (0 if not paused or no end time)."""
        if not self.is_paused or not self.resume_at:
            return 0.0
        remaining = (self.resume_at - datetime.now()).total_seconds()
        return max(0.0, remaining)
    
    @property
    def time_remaining_formatted(self) -> str:
        """Human-readable time remaining."""
        seconds = self.time_remaining
        if seconds <= 0:
            return "Ready"
        minutes = int(seconds // 60)
        hours = int(minutes // 60)
        if hours > 0:
            return f"{hours}h {minutes % 60}m"
        elif minutes > 0:
            return f"{minutes}m {int(seconds % 60)}s"
        else:
            return f"{int(seconds)}s"


class AutoPause:
    """
    Automatically pauses account actions when risks are detected.
    
    Features:
    - Configurable pause durations per reason
    - Auto-resume after pause period
    - Escalating pause durations for repeated issues
    - Callback notifications
    
    Example:
        auto_pause = AutoPause()
        
        # Check before action
        if auto_pause.should_pause("account_123"):
            state = auto_pause.get_state("account_123")
            print(f"Paused: {state.reason.value}, resume in {state.time_remaining_formatted}")
            return
        
        # Trigger pause on issue
        auto_pause.pause(
            "account_123",
            reason=PauseReason.ACTION_BLOCK,
            duration_minutes=60
        )
    """
    
    # Default pause durations (minutes) per reason
    DEFAULT_DURATIONS = {
        PauseReason.RATE_LIMIT: 15,
        PauseReason.ACTION_BLOCK: 60,
        PauseReason.LOW_HEALTH_SCORE: 30,
        PauseReason.CRITICAL_SIGNAL: 120,
        PauseReason.MANUAL: 60,
        PauseReason.SLEEP_HOURS: 480,  # 8 hours
        PauseReason.WARMUP_LIMIT: 60,
        PauseReason.UNKNOWN: 30,
    }
    
    def __init__(
        self,
        default_duration_minutes: int = 60,
        escalation_multiplier: float = 1.5,
        max_escalation: int = 5,
        auto_resume: bool = True,
        on_pause_callback: Optional[Callable] = None,
        on_resume_callback: Optional[Callable] = None
    ):
        """
        Initialize the auto-pause controller.
        
        Args:
            default_duration_minutes: Default pause duration
            escalation_multiplier: Multiply duration on repeated pauses
            max_escalation: Maximum escalation level
            auto_resume: Automatically resume after pause period
            on_pause_callback: Called when pause starts (account_id, reason)
            on_resume_callback: Called when pause ends (account_id)
        """
        self.default_duration = default_duration_minutes
        self.escalation_multiplier = escalation_multiplier
        self.max_escalation = max_escalation
        self.auto_resume = auto_resume
        self.on_pause = on_pause_callback
        self.on_resume = on_resume_callback
        
        # Per-account state
        self._states: Dict[str, PauseState] = {}
        self._escalation_levels: Dict[str, int] = {}
        
        # Thread for auto-resume
        self._lock = threading.Lock()
        if auto_resume:
            self._resume_thread = threading.Thread(target=self._resume_checker, daemon=True)
            self._resume_thread.start()
        
        logger.info(
            f"AutoPause initialized: default={default_duration_minutes}m, "
            f"escalation={escalation_multiplier}x"
        )
    
    def pause(
        self,
        account_id: str,
        reason: PauseReason = PauseReason.UNKNOWN,
        duration_minutes: Optional[int] = None,
        escalate: bool = True
    ) -> PauseState:
        """
        Pause an account.
        
        Args:
            account_id: Account to pause
            reason: Reason for pausing
            duration_minutes: Pause duration (uses default if None)
            escalate: Apply escalation for repeated pauses
            
        Returns:
            Updated PauseState
        """
        with self._lock:
            # Get or create state
            if account_id not in self._states:
                self._states[account_id] = PauseState(
                    account_id=account_id,
                    is_paused=False,
                    reason=None,
                    paused_at=None,
                    resume_at=None,
                    pause_count=0
                )
            
            state = self._states[account_id]
            
            # Calculate duration
            if duration_minutes is None:
                duration_minutes = self.DEFAULT_DURATIONS.get(reason, self.default_duration)
            
            # Apply escalation
            if escalate:
                level = self._escalation_levels.get(account_id, 0)
                if level > 0:
                    duration_minutes = int(duration_minutes * (self.escalation_multiplier ** min(level, self.max_escalation)))
                self._escalation_levels[account_id] = level + 1
            
            # Update state
            now = datetime.now()
            state.is_paused = True
            state.reason = reason
            state.paused_at = now
            state.resume_at = now + timedelta(minutes=duration_minutes)
            state.pause_count += 1
            
            logger.warning(
                f"Account {account_id} PAUSED: {reason.value} "
                f"for {duration_minutes}m (escalation level: {self._escalation_levels.get(account_id, 0)})"
            )
            
            # Callback
            if self.on_pause:
                try:
                    self.on_pause(account_id, reason)
                except Exception as e:
                    logger.error(f"Pause callback error: {e}")
            
            return state
    
    def resume(self, account_id: str, reset_escalation: bool = False) -> PauseState:
        """
        Resume an account.
        
        Args:
            account_id: Account to resume
            reset_escalation: Reset escalation level
            
        Returns:
            Updated PauseState
        """
        with self._lock:
            if account_id not in self._states:
                self._states[account_id] = PauseState(
                    account_id=account_id,
                    is_paused=False,
                    reason=None,
                    paused_at=None,
                    resume_at=None,
                    pause_count=0
                )
                return self._states[account_id]
            
            state = self._states[account_id]
            was_paused = state.is_paused
            
            state.is_paused = False
            state.reason = None
            state.paused_at = None
            state.resume_at = None
            
            if reset_escalation:
                self._escalation_levels[account_id] = 0
            
            if was_paused:
                logger.info(f"Account {account_id} RESUMED")
                
                # Callback
                if self.on_resume:
                    try:
                        self.on_resume(account_id)
                    except Exception as e:
                        logger.error(f"Resume callback error: {e}")
            
            return state
    
    def should_pause(self, account_id: str) -> bool:
        """
        Check if an account should be paused.
        
        Args:
            account_id: Account to check
            
        Returns:
            True if account is paused
        """
        with self._lock:
            if account_id not in self._states:
                return False
            
            state = self._states[account_id]
            
            if not state.is_paused:
                return False
            
            # Check if pause has expired
            if state.resume_at and datetime.now() >= state.resume_at:
                # Auto-resume
                self.resume(account_id)
                return False
            
            return True
    
    def get_state(self, account_id: str) -> PauseState:
        """
        Get current pause state for an account.
        
        Args:
            account_id: Account to check
            
        Returns:
            PauseState for the account
        """
        with self._lock:
            if account_id not in self._states:
                return PauseState(
                    account_id=account_id,
                    is_paused=False,
                    reason=None,
                    paused_at=None,
                    resume_at=None,
                    pause_count=0
                )
            return self._states[account_id]
    
    def get_all_paused(self) -> List[str]:
        """
        Get list of all currently paused accounts.
        
        Returns:
            List of account IDs that are paused
        """
        with self._lock:
            return [
                account_id for account_id, state in self._states.items()
                if state.is_paused
            ]
    
    def get_escalation_level(self, account_id: str) -> int:
        """
        Get current escalation level for an account.
        
        Args:
            account_id: Account to check
            
        Returns:
            Escalation level (0 = no escalation)
        """
        with self._lock:
            return self._escalation_levels.get(account_id, 0)
    
    def reset_escalation(self, account_id: Optional[str] = None) -> None:
        """
        Reset escalation level.
        
        Args:
            account_id: Account to reset, or None for all
        """
        with self._lock:
            if account_id:
                self._escalation_levels[account_id] = 0
                logger.debug(f"Reset escalation for {account_id}")
            else:
                self._escalation_levels.clear()
                logger.debug("Reset all escalation levels")
    
    def _resume_checker(self) -> None:
        """Background thread to auto-resume accounts."""
        while True:
            try:
                now = datetime.now()
                accounts_to_resume = []
                
                with self._lock:
                    for account_id, state in self._states.items():
                        if state.is_paused and state.resume_at and now >= state.resume_at:
                            accounts_to_resume.append(account_id)
                
                for account_id in accounts_to_resume:
                    self.resume(account_id)
                
            except Exception as e:
                logger.error(f"Resume checker error: {e}")
            
            time.sleep(10)  # Check every 10 seconds
    
    def pause_from_signal(
        self,
        account_id: str,
        signal_type: str,
        severity: int
    ) -> Optional[PauseState]:
        """
        Pause based on a detected signal.
        
        Args:
            account_id: Account to pause
            signal_type: Type of signal detected
            severity: Severity level (1-4)
            
        Returns:
            PauseState if paused, None if no pause needed
        """
        # Map signal types to pause reasons
        reason_map = {
            "rate_limit": PauseReason.RATE_LIMIT,
            "action_block": PauseReason.ACTION_BLOCK,
            "temporary_ban": PauseReason.CRITICAL_SIGNAL,
            "permanent_ban": PauseReason.CRITICAL_SIGNAL,
        }
        
        reason = reason_map.get(signal_type, PauseReason.UNKNOWN)
        
        # Determine if we should pause based on severity
        if severity >= 3:  # HIGH or CRITICAL
            return self.pause(account_id, reason)
        elif severity == 2:  # MEDIUM - shorter pause
            return self.pause(account_id, reason, duration_minutes=15)
        
        return None
