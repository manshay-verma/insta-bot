"""
Orchestrator Adapters

Unified interface for all automation modules.
"""

from .base_adapter import BaseAdapter, AdapterType
from .playwright_adapter import PlaywrightAdapter
from .selenium_adapter import SeleniumAdapter
from .scrapy_adapter import ScrapyAdapter
from .downloader_adapter import DownloaderAdapter
from .safety_adapter import SafetyAdapter

__all__ = [
    "BaseAdapter",
    "AdapterType",
    "PlaywrightAdapter",
    "SeleniumAdapter",
    "ScrapyAdapter",
    "DownloaderAdapter",
    "SafetyAdapter",
]
