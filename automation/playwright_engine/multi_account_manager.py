import asyncio
import json
import os
import random
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from browser_manager import InstagramBrowser

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class AccountInfo:
    """Represents a single Instagram account with its session state."""
    username: str
    password: str
    cookie_path: str
    is_active: bool = False
    last_used: Optional[datetime] = None
    actions_today: int = 0
    is_banned: bool = False
    cooldown_until: Optional[datetime] = None
    proxy: Optional[Dict] = None

    def to_dict(self, include_credentials: bool = True) -> Dict:
        data = {
            'username': self.username,
            'is_active': self.is_active,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'actions_today': self.actions_today,
            'is_banned': self.is_banned,
            'cooldown_until': self.cooldown_until.isoformat() if self.cooldown_until else None,
            'cookie_path': self.cookie_path,
            'proxy': self.proxy
        }
        if include_credentials:
            data['password'] = self.password
        return data


class MultiAccountManager:
    """
    Manages multiple Instagram accounts with session rotation.
    
    Features:
    - Load/save account configurations
    - Rotate between accounts based on usage and cooldowns
    - Track actions per account
    - Handle banned/rate-limited accounts
    - Automatic cooldown management
    """
    
    def __init__(self, config_path: str = "accounts_config.json", headless: bool = True, browser_type: str = "chromium", channel: str = "chrome"):
        self.config_path = config_path
        self.headless = headless
        self.browser_type = browser_type
        self.channel = channel
        self.accounts: List[AccountInfo] = []
        self.current_account: Optional[AccountInfo] = None
        self.browser: Optional[InstagramBrowser] = None
        
        # Settings
        self.max_actions_per_account = 50  # Per day
        self.cooldown_minutes = 30  # Between account switches
        self.rotation_strategy = "round_robin"  # or "least_used" or "random"
        
        # Auto-load if config exists
        self.load_state()
        
    def add_account(self, username: str, password: str, cookie_path: Optional[str] = None, 
                    proxy: Optional[Dict] = None):
        """Add a new account to the manager."""
        if cookie_path is None:
            cookie_path = f"cookies_{username}.json"
        
        # Check if account already exists
        for acc in self.accounts:
            if acc.username == username:
                logger.warning(f"Account {username} already exists. Updating...")
                acc.password = password
                acc.cookie_path = cookie_path
                acc.proxy = proxy
                self.save_state()
                return
        
        account = AccountInfo(
            username=username,
            password=password,
            cookie_path=cookie_path,
            proxy=proxy
        )
        self.accounts.append(account)
        logger.info(f"Added account: {username}")
        self.save_state()
        
    def remove_account(self, username: str):
        """Remove an account from the manager."""
        self.accounts = [acc for acc in self.accounts if acc.username != username]
        logger.info(f"Removed account: {username}")
        self.save_state()
        
    def load_accounts(self, accounts_data: List[Dict]):
        """
        Load accounts from a list of dictionaries.
        """
        for acc_data in accounts_data:
            self.add_account(
                username=acc_data['username'],
                password=acc_data['password'],
                cookie_path=acc_data.get('cookie_path'),
                proxy=acc_data.get('proxy')
            )
            
    def save_state(self):
        """Save current account states to config file including credentials."""
        state = {
            'accounts': [acc.to_dict(include_credentials=True) for acc in self.accounts],
            'last_saved': datetime.now().isoformat()
        }
        with open(self.config_path, 'w') as f:
            json.dump(state, f, indent=2)
        logger.info(f"Saved all accounts and state to {self.config_path}")
        
    def load_state(self):
        """Load account states and credentials from config file."""
        if not os.path.exists(self.config_path):
            return
            
        try:
            with open(self.config_path, 'r') as f:
                state = json.load(f)
                
            self.accounts = []
            for saved_acc in state.get('accounts', []):
                acc = AccountInfo(
                    username=saved_acc['username'],
                    password=saved_acc.get('password', ''),
                    cookie_path=saved_acc.get('cookie_path', f"cookies_{saved_acc['username']}.json"),
                    proxy=saved_acc.get('proxy'),
                    actions_today=saved_acc.get('actions_today', 0),
                    is_banned=saved_acc.get('is_banned', False)
                )
                if saved_acc.get('cooldown_until'):
                    acc.cooldown_until = datetime.fromisoformat(saved_acc['cooldown_until'])
                if saved_acc.get('last_used'):
                    acc.last_used = datetime.fromisoformat(saved_acc['last_used'])
                
                self.accounts.append(acc)
                            
            logger.info(f"Loaded {len(self.accounts)} accounts from config")
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
        
    def get_available_accounts(self) -> List[AccountInfo]:
        """Get list of accounts that are available for use (not banned, not on cooldown)."""
        now = datetime.now()
        available = []
        
        for acc in self.accounts:
            # Skip banned accounts
            if acc.is_banned:
                continue
            
            # Skip accounts on cooldown
            if acc.cooldown_until and acc.cooldown_until > now:
                continue
                
            # Skip accounts that have hit daily limit
            if acc.actions_today >= self.max_actions_per_account:
                continue
                
            available.append(acc)
            
        return available
        
    def select_next_account(self) -> Optional[AccountInfo]:
        """Select the next account based on rotation strategy."""
        available = self.get_available_accounts()
        
        if not available:
            logger.warning("No available accounts!")
            return None
            
        if self.rotation_strategy == "round_robin":
            # Pick the account that was used least recently
            available.sort(key=lambda x: x.last_used or datetime.min)
            return available[0]
            
        elif self.rotation_strategy == "least_used":
            # Pick the account with fewest actions today
            available.sort(key=lambda x: x.actions_today)
            return available[0]
            
        elif self.rotation_strategy == "random":
            return random.choice(available)
            
        return available[0]
        
    async def switch_account(self, account: Optional[AccountInfo] = None) -> bool:
        """
        Switch to a different account.
        If no account specified, auto-selects based on rotation strategy.
        """
        # Close current browser if open
        if self.browser:
            await self.browser.close()
            self.browser = None
            
        # Set cooldown for current account
        if self.current_account:
            self.current_account.is_active = False
            self.current_account.cooldown_until = datetime.now() + timedelta(minutes=self.cooldown_minutes)
            logger.info(f"Account {self.current_account.username} put on cooldown")
            
        # Select next account if not specified
        if account is None:
            account = self.select_next_account()
            
        if account is None:
            logger.error("No account available for switching")
            return False
            
        # Create new browser with account's proxy and global settings
        self.browser = InstagramBrowser(
            headless=self.headless,
            proxy=account.proxy,
            browser_type=self.browser_type,
            channel=self.channel
        )
        await self.browser.start()
        
        # Login to the account
        try:
            await self.browser.login(
                username=account.username,
                password=account.password,
                cookie_path=account.cookie_path
            )
            
            # Verify session is valid
            if await self.browser.is_session_valid():
                account.is_active = True
                account.last_used = datetime.now()
                self.current_account = account
                logger.info(f"Switched to account: {account.username}")
                self.save_state()
                return True
            else:
                logger.error(f"Failed to validate session for {account.username}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to switch to account {account.username}: {e}")
            return False
            
    async def switch_to_account(self, username: str) -> bool:
        """Switch to a specific account by username."""
        for acc in self.accounts:
            if acc.username == username:
                return await self.switch_account(acc)
        logger.error(f"Account {username} not found")
        return False
        
    def record_action(self, action_type: str = "general"):
        """Record an action for the current account."""
        if self.current_account:
            self.current_account.actions_today += 1
            self.current_account.last_used = datetime.now()
            logger.debug(f"Recorded action for {self.current_account.username}: {action_type}")
            
    def mark_banned(self, username: Optional[str] = None):
        """Mark an account as banned."""
        target = None
        if username:
            for acc in self.accounts:
                if acc.username == username:
                    target = acc
                    break
        else:
            target = self.current_account
            
        if target:
            target.is_banned = True
            target.is_active = False
            logger.warning(f"Account marked as banned: {target.username}")
            self.save_state()
            
    def reset_daily_counts(self):
        """Reset action counts for all accounts (call at midnight)."""
        for acc in self.accounts:
            acc.actions_today = 0
        logger.info("Reset daily action counts for all accounts")
        self.save_state()
        
    def get_status(self) -> Dict:
        """Get status of all accounts."""
        return {
            'total_accounts': len(self.accounts),
            'available_accounts': len(self.get_available_accounts()),
            'current_account': self.current_account.username if self.current_account else None,
            'accounts': [
                {
                    'username': acc.username,
                    'is_active': acc.is_active,
                    'is_banned': acc.is_banned,
                    'actions_today': acc.actions_today,
                    'on_cooldown': acc.cooldown_until > datetime.now() if acc.cooldown_until else False
                }
                for acc in self.accounts
            ]
        }
        
    async def close(self):
        """Close the manager and save state."""
        if self.browser:
            await self.browser.close()
        if self.current_account:
            self.current_account.is_active = False
        self.save_state()
        logger.info("MultiAccountManager closed")
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
