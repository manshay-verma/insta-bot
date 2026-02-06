"""
Warmup Manager

Manages gradual increase in activity limits for new accounts.
New accounts start with reduced limits that gradually increase over time.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass, field
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class WarmupConfig:
    """Configuration for account warmup."""
    warmup_days: int = 7
    initial_multiplier: float = 0.3  # Start at 30% of normal limits
    final_multiplier: float = 1.0    # End at 100% of normal limits
    # Days to reach each milestone (optional granular control)
    milestones: Dict[int, float] = field(default_factory=lambda: {
        1: 0.3,   # Day 1: 30%
        3: 0.5,   # Day 3: 50%
        5: 0.7,   # Day 5: 70%
        7: 1.0,   # Day 7: 100%
    })


@dataclass
class AccountWarmupState:
    """State for a single account's warmup progress."""
    account_id: str
    created_at: datetime
    warmup_started_at: datetime
    current_multiplier: float = 0.3
    is_warmed_up: bool = False
    total_actions_performed: int = 0


class WarmupManager:
    """
    Manages warmup protocol for new Instagram accounts.
    
    Features:
    - Gradual limit increase over configurable period
    - Per-account state tracking
    - Persistence to file
    - Configurable milestones
    
    Example:
        manager = WarmupManager(warmup_days=7)
        
        # Get multiplier for account
        multiplier = manager.get_multiplier("account_123")
        adjusted_limit = int(60 * multiplier)  # 60 actions/hr * warmup multiplier
        
        # Record an action
        manager.record_action("account_123")
    """
    
    def __init__(
        self,
        warmup_days: int = 7,
        initial_multiplier: float = 0.3,
        state_file: Optional[str] = None
    ):
        """
        Initialize the warmup manager.
        
        Args:
            warmup_days: Number of days for full warmup
            initial_multiplier: Starting limit multiplier (0.0 to 1.0)
            state_file: Optional file path to persist state
        """
        self.warmup_days = warmup_days
        self.initial_multiplier = initial_multiplier
        self.state_file = state_file
        
        # Account states
        self._accounts: Dict[str, AccountWarmupState] = {}
        
        # Load existing state
        if state_file and os.path.exists(state_file):
            self._load_state()
        
        logger.info(
            f"WarmupManager initialized: "
            f"{warmup_days} days, starting at {initial_multiplier*100:.0f}%"
        )
    
    def register_account(
        self,
        account_id: str,
        created_at: Optional[datetime] = None
    ) -> AccountWarmupState:
        """
        Register a new account for warmup tracking.
        
        Args:
            account_id: Unique identifier for the account
            created_at: When the account was created (default: now)
            
        Returns:
            AccountWarmupState for the account
        """
        if account_id in self._accounts:
            logger.debug(f"Account {account_id} already registered")
            return self._accounts[account_id]
        
        now = datetime.now()
        state = AccountWarmupState(
            account_id=account_id,
            created_at=created_at or now,
            warmup_started_at=now,
            current_multiplier=self.initial_multiplier
        )
        self._accounts[account_id] = state
        self._save_state()
        
        logger.info(f"Registered account for warmup: {account_id}")
        return state
    
    def get_multiplier(self, account_id: str) -> float:
        """
        Get the current limit multiplier for an account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            Multiplier (0.0 to 1.0) to apply to rate limits
        """
        if account_id not in self._accounts:
            # Auto-register unknown accounts
            self.register_account(account_id)
        
        state = self._accounts[account_id]
        
        if state.is_warmed_up:
            return 1.0
        
        # Calculate days since warmup started
        days_elapsed = (datetime.now() - state.warmup_started_at).days
        
        if days_elapsed >= self.warmup_days:
            # Warmup complete
            state.is_warmed_up = True
            state.current_multiplier = 1.0
            self._save_state()
            logger.info(f"Account {account_id} warmup complete!")
            return 1.0
        
        # Linear interpolation
        progress = days_elapsed / self.warmup_days
        multiplier = self.initial_multiplier + (1.0 - self.initial_multiplier) * progress
        
        state.current_multiplier = multiplier
        return multiplier
    
    def get_adjusted_limit(
        self,
        account_id: str,
        base_limit: int
    ) -> int:
        """
        Get the adjusted limit for an account based on warmup status.
        
        Args:
            account_id: Account identifier
            base_limit: Normal limit value
            
        Returns:
            Adjusted limit (may be lower during warmup)
        """
        multiplier = self.get_multiplier(account_id)
        adjusted = int(base_limit * multiplier)
        
        # Ensure at least 1 action is allowed
        return max(1, adjusted)
    
    def record_action(self, account_id: str, count: int = 1) -> None:
        """
        Record that actions were performed by an account.
        
        Args:
            account_id: Account identifier
            count: Number of actions performed
        """
        if account_id not in self._accounts:
            self.register_account(account_id)
        
        self._accounts[account_id].total_actions_performed += count
        logger.debug(f"Recorded {count} action(s) for {account_id}")
    
    def get_warmup_status(self, account_id: str) -> Dict:
        """
        Get detailed warmup status for an account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            Dictionary with warmup details
        """
        if account_id not in self._accounts:
            return {"error": "Account not found", "registered": False}
        
        state = self._accounts[account_id]
        days_elapsed = (datetime.now() - state.warmup_started_at).days
        days_remaining = max(0, self.warmup_days - days_elapsed)
        
        return {
            "account_id": account_id,
            "registered": True,
            "is_warmed_up": state.is_warmed_up,
            "days_elapsed": days_elapsed,
            "days_remaining": days_remaining,
            "current_multiplier": self.get_multiplier(account_id),
            "current_percent": f"{self.get_multiplier(account_id)*100:.0f}%",
            "total_actions": state.total_actions_performed,
            "warmup_started": state.warmup_started_at.isoformat(),
        }
    
    def reset_warmup(self, account_id: str) -> None:
        """
        Reset warmup for an account (restart from beginning).
        
        Args:
            account_id: Account identifier
        """
        if account_id in self._accounts:
            state = self._accounts[account_id]
            state.warmup_started_at = datetime.now()
            state.is_warmed_up = False
            state.current_multiplier = self.initial_multiplier
            state.total_actions_performed = 0
            self._save_state()
            logger.info(f"Reset warmup for account: {account_id}")
    
    def mark_warmed_up(self, account_id: str) -> None:
        """
        Manually mark an account as fully warmed up.
        
        Args:
            account_id: Account identifier
        """
        if account_id not in self._accounts:
            self.register_account(account_id)
        
        state = self._accounts[account_id]
        state.is_warmed_up = True
        state.current_multiplier = 1.0
        self._save_state()
        logger.info(f"Manually marked account as warmed up: {account_id}")
    
    def _save_state(self) -> None:
        """Save state to file if configured."""
        if not self.state_file:
            return
        
        try:
            data = {}
            for account_id, state in self._accounts.items():
                data[account_id] = {
                    "account_id": state.account_id,
                    "created_at": state.created_at.isoformat(),
                    "warmup_started_at": state.warmup_started_at.isoformat(),
                    "current_multiplier": state.current_multiplier,
                    "is_warmed_up": state.is_warmed_up,
                    "total_actions_performed": state.total_actions_performed,
                }
            
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved warmup state to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save warmup state: {e}")
    
    def _load_state(self) -> None:
        """Load state from file if it exists."""
        if not self.state_file or not os.path.exists(self.state_file):
            return
        
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            
            for account_id, state_data in data.items():
                self._accounts[account_id] = AccountWarmupState(
                    account_id=state_data["account_id"],
                    created_at=datetime.fromisoformat(state_data["created_at"]),
                    warmup_started_at=datetime.fromisoformat(state_data["warmup_started_at"]),
                    current_multiplier=state_data["current_multiplier"],
                    is_warmed_up=state_data["is_warmed_up"],
                    total_actions_performed=state_data.get("total_actions_performed", 0),
                )
            
            logger.info(f"Loaded warmup state for {len(self._accounts)} accounts")
        except Exception as e:
            logger.error(f"Failed to load warmup state: {e}")
