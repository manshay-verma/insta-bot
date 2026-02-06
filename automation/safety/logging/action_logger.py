"""
Action Logger

Structured action logging for audit trails and debugging.
Logs all actions performed with context for analysis.
"""

import logging
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import threading

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log levels for actions."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ActionLog:
    """Represents a single logged action."""
    timestamp: datetime
    account_id: str
    action_type: str
    target: str  # Target of action (user ID, post URL, etc.)
    success: bool
    level: LogLevel = LogLevel.INFO
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["level"] = self.level.value
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ActionLog":
        """Create from dictionary."""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["level"] = LogLevel(data["level"])
        return cls(**data)


class ActionLogger:
    """
    Structured action logger for audit trails.
    
    Features:
    - JSON-formatted action logs
    - File and console output
    - Per-account log files
    - Log rotation
    - Query interface for analysis
    
    Example:
        action_logger = ActionLogger(log_dir="./logs/actions")
        
        # Log an action
        action_logger.log_action(
            account_id="my_account",
            action_type="like",
            target="https://instagram.com/p/ABC123",
            success=True,
            duration_ms=1523.5,
            metadata={"post_owner": "user123"}
        )
        
        # Query logs
        recent = action_logger.get_recent_logs("my_account", limit=100)
    """
    
    def __init__(
        self,
        log_dir: Optional[str] = None,
        console_output: bool = True,
        file_output: bool = True,
        json_format: bool = True,
        max_file_size_mb: int = 10,
        max_files: int = 5
    ):
        """
        Initialize the action logger.
        
        Args:
            log_dir: Directory for log files (default: ./logs/actions)
            console_output: Also log to console
            file_output: Write to log files
            json_format: Use JSON format (otherwise plain text)
            max_file_size_mb: Maximum size per log file before rotation
            max_files: Maximum number of rotated files to keep
        """
        self.log_dir = Path(log_dir) if log_dir else Path("./logs/actions")
        self.console_output = console_output
        self.file_output = file_output
        self.json_format = json_format
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.max_files = max_files
        
        # In-memory log buffer (recent logs)
        self._buffer: List[ActionLog] = []
        self._buffer_max = 1000
        self._lock = threading.Lock()
        
        # Create log directory
        if file_output:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ActionLogger initialized: dir={self.log_dir}")
    
    def log_action(
        self,
        account_id: str,
        action_type: str,
        target: str,
        success: bool,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
        level: LogLevel = LogLevel.INFO,
        **metadata
    ) -> ActionLog:
        """
        Log an action.
        
        Args:
            account_id: Account that performed the action
            action_type: Type of action (like, follow, etc.)
            target: Target of the action
            success: Whether the action succeeded
            duration_ms: How long the action took
            error: Error message if failed
            error_code: Error code if failed
            level: Log level
            **metadata: Additional context
            
        Returns:
            The created ActionLog
        """
        log_entry = ActionLog(
            timestamp=datetime.now(),
            account_id=account_id,
            action_type=action_type,
            target=target,
            success=success,
            duration_ms=duration_ms,
            error=error,
            error_code=error_code,
            level=level,
            metadata=metadata
        )
        
        # Store in buffer
        with self._lock:
            self._buffer.append(log_entry)
            if len(self._buffer) > self._buffer_max:
                self._buffer.pop(0)
        
        # Write to outputs
        self._write_log(log_entry)
        
        return log_entry
    
    def log_success(
        self,
        account_id: str,
        action_type: str,
        target: str,
        duration_ms: Optional[float] = None,
        **metadata
    ) -> ActionLog:
        """Convenience method for successful actions."""
        return self.log_action(
            account_id=account_id,
            action_type=action_type,
            target=target,
            success=True,
            duration_ms=duration_ms,
            level=LogLevel.INFO,
            **metadata
        )
    
    def log_failure(
        self,
        account_id: str,
        action_type: str,
        target: str,
        error: str,
        error_code: Optional[str] = None,
        duration_ms: Optional[float] = None,
        **metadata
    ) -> ActionLog:
        """Convenience method for failed actions."""
        return self.log_action(
            account_id=account_id,
            action_type=action_type,
            target=target,
            success=False,
            error=error,
            error_code=error_code,
            duration_ms=duration_ms,
            level=LogLevel.ERROR,
            **metadata
        )
    
    def _write_log(self, log_entry: ActionLog) -> None:
        """Write log entry to outputs."""
        # Format the log
        if self.json_format:
            log_line = log_entry.to_json()
        else:
            log_line = self._format_plain(log_entry)
        
        # Console output
        if self.console_output:
            log_level = getattr(logging, log_entry.level.value.upper(), logging.INFO)
            logger.log(log_level, log_line)
        
        # File output
        if self.file_output:
            self._write_to_file(log_entry.account_id, log_line)
    
    def _format_plain(self, log_entry: ActionLog) -> str:
        """Format log entry as plain text."""
        status = "✓" if log_entry.success else "✗"
        duration = f" ({log_entry.duration_ms:.0f}ms)" if log_entry.duration_ms else ""
        error_part = f" - {log_entry.error}" if log_entry.error else ""
        
        return (
            f"[{log_entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
            f"[{log_entry.account_id}] "
            f"{status} {log_entry.action_type} -> {log_entry.target}"
            f"{duration}{error_part}"
        )
    
    def _write_to_file(self, account_id: str, log_line: str) -> None:
        """Write log line to account-specific file."""
        try:
            log_file = self.log_dir / f"{account_id}.log"
            
            # Check for rotation
            if log_file.exists() and log_file.stat().st_size > self.max_file_size:
                self._rotate_file(log_file)
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
                
        except Exception as e:
            logger.error(f"Failed to write to log file: {e}")
    
    def _rotate_file(self, log_file: Path) -> None:
        """Rotate log file."""
        try:
            # Rotate existing numbered files
            for i in range(self.max_files - 1, 0, -1):
                old_file = log_file.with_suffix(f".log.{i}")
                new_file = log_file.with_suffix(f".log.{i + 1}")
                if old_file.exists():
                    if i + 1 > self.max_files:
                        old_file.unlink()
                    else:
                        old_file.rename(new_file)
            
            # Rotate current file
            log_file.rename(log_file.with_suffix(".log.1"))
            
        except Exception as e:
            logger.error(f"Failed to rotate log file: {e}")
    
    def get_recent_logs(
        self,
        account_id: Optional[str] = None,
        action_type: Optional[str] = None,
        success_only: Optional[bool] = None,
        limit: int = 100
    ) -> List[ActionLog]:
        """
        Get recent logs from memory buffer.
        
        Args:
            account_id: Filter by account
            action_type: Filter by action type
            success_only: Filter by success status
            limit: Maximum logs to return
            
        Returns:
            List of matching logs (newest first)
        """
        with self._lock:
            logs = list(reversed(self._buffer))
        
        # Apply filters
        if account_id:
            logs = [l for l in logs if l.account_id == account_id]
        
        if action_type:
            logs = [l for l in logs if l.action_type == action_type]
        
        if success_only is not None:
            logs = [l for l in logs if l.success == success_only]
        
        return logs[:limit]
    
    def get_statistics(
        self,
        account_id: Optional[str] = None,
        since_hours: int = 24
    ) -> Dict:
        """
        Get action statistics from buffer.
        
        Args:
            account_id: Filter by account
            since_hours: Time window
            
        Returns:
            Dictionary of statistics
        """
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=since_hours)
        
        with self._lock:
            logs = [l for l in self._buffer if l.timestamp >= cutoff]
        
        if account_id:
            logs = [l for l in logs if l.account_id == account_id]
        
        if not logs:
            return {"total": 0, "success": 0, "failure": 0, "success_rate": 0.0}
        
        total = len(logs)
        success = sum(1 for l in logs if l.success)
        failure = total - success
        
        # Group by action type
        by_type = {}
        for log in logs:
            if log.action_type not in by_type:
                by_type[log.action_type] = {"total": 0, "success": 0}
            by_type[log.action_type]["total"] += 1
            if log.success:
                by_type[log.action_type]["success"] += 1
        
        # Average duration
        durations = [l.duration_ms for l in logs if l.duration_ms]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "total": total,
            "success": success,
            "failure": failure,
            "success_rate": success / total,
            "avg_duration_ms": avg_duration,
            "by_action_type": by_type,
            "since_hours": since_hours
        }
    
    def export_logs(
        self,
        output_path: str,
        account_id: Optional[str] = None,
        format: str = "json"
    ) -> int:
        """
        Export logs to a file.
        
        Args:
            output_path: Path to output file
            account_id: Filter by account
            format: Output format ("json" or "csv")
            
        Returns:
            Number of logs exported
        """
        with self._lock:
            logs = list(self._buffer)
        
        if account_id:
            logs = [l for l in logs if l.account_id == account_id]
        
        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump([l.to_dict() for l in logs], f, indent=2)
        elif format == "csv":
            import csv
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "account_id", "action_type", "target",
                    "success", "duration_ms", "error", "error_code"
                ])
                for log in logs:
                    writer.writerow([
                        log.timestamp.isoformat(),
                        log.account_id,
                        log.action_type,
                        log.target,
                        log.success,
                        log.duration_ms,
                        log.error,
                        log.error_code
                    ])
        
        logger.info(f"Exported {len(logs)} logs to {output_path}")
        return len(logs)
    
    def clear_buffer(self) -> None:
        """Clear the in-memory log buffer."""
        with self._lock:
            self._buffer.clear()
        logger.info("Cleared action log buffer")
