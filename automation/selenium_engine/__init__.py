"""
Selenium Backup Module

Provides Selenium-based automation as a backup for Playwright.
"""

from .driver_manager import DriverManager, BrowserType
from .stealth_config import StealthConfig, apply_stealth
from .navigation import SeleniumNavigator
from .fallback_handler import FallbackHandler

__all__ = [
    "DriverManager",
    "BrowserType",
    "StealthConfig",
    "apply_stealth",
    "SeleniumNavigator",
    "FallbackHandler",
]
