"""
Orchestrator Module

Bridges automation scripts with backend API.
"""

from .api_client import InstaApiClient, ApiResponse, AccountStatus, BotAction
from .callbacks import ActionCallback, ActionType, ActionResult
from .cookie_sync import CookieSync
from .bot_worker import BotWorker, TaskConfig, WorkerResult
from .bot_worker import TaskType as LegacyTaskType
from .unified_worker import UnifiedWorker, UnifiedResult
from .adapters import (
    BaseAdapter,
    AdapterType,
    PlaywrightAdapter,
    SeleniumAdapter,
    ScrapyAdapter,
    DownloaderAdapter,
    SafetyAdapter,
)
from .adapters.base_adapter import TaskType, TaskResult

__all__ = [
    # API Client
    "InstaApiClient",
    "ApiResponse",
    "AccountStatus",
    "BotAction",
    
    # Callbacks
    "ActionCallback",
    "ActionType",
    "ActionResult",
    
    # Cookie Sync
    "CookieSync",
    
    # Original Worker (Playwright only)
    "BotWorker",
    "TaskConfig",
    "WorkerResult",
    "LegacyTaskType",
    
    # Unified Worker (all backends)
    "UnifiedWorker",
    "UnifiedResult",
    "TaskType",
    "TaskResult",
    
    # Adapters
    "BaseAdapter",
    "AdapterType",
    "PlaywrightAdapter",
    "SeleniumAdapter",
    "ScrapyAdapter",
    "DownloaderAdapter",
    "SafetyAdapter",
]
