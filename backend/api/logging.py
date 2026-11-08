import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set, Union

REDACTED_STRING = "[REDACTED]"

# Case-insensitive substring matching for sensitive keys
SENSITIVE_KEY_PATTERNS = {
    "password",
    "token",
    "secret",
    "cookie",
    "cookies",
    "session",
    "session_data",
    "session_contents",
    "otp",
    "verification_code",
    "code",
    "key",
    "auth",
    "authorization",
    "credential",
    "owner_token",
    "owner_token_hash",
    "lock_owner_token",
}

# Regex to detect sensitive values (e.g. Bearer tokens, hex hashes, cookie strings)
SENSITIVE_VALUE_REGEXES = [
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    re.compile(r"sessionid=[A-Za-z0-9%_\-]+", re.IGNORECASE),
    re.compile(r"csrftoken=[A-Za-z0-9%_\-]+", re.IGNORECASE),
    re.compile(r"ds_user_id=\d+", re.IGNORECASE),
]


def is_sensitive_key(key: str) -> bool:
    if not isinstance(key, str):
        return False
    lower = key.lower()
    return any(pattern in lower for pattern in SENSITIVE_KEY_PATTERNS)


def redact_sensitive_data(val: Any) -> Any:
    """Recursively redact credentials, cookies, tokens, and secrets from data."""
    if isinstance(val, dict):
        cleaned = {}
        for k, v in val.items():
            if is_sensitive_key(str(k)):
                cleaned[k] = REDACTED_STRING
            else:
                cleaned[k] = redact_sensitive_data(v)
        return cleaned
    elif isinstance(val, (list, tuple, set)):
        items = [redact_sensitive_data(item) for item in val]
        return type(val)(items) if not isinstance(val, set) else set(items)
    elif isinstance(val, str):
        redacted_str = val
        for regex in SENSITIVE_VALUE_REGEXES:
            redacted_str = regex.sub(REDACTED_STRING, redacted_str)
        return redacted_str
    return val


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that sanitizes records before emitting.
    Guarantees secrets, cookies, owner tokens, and passwords never reach log output.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for regex in SENSITIVE_VALUE_REGEXES:
                record.msg = regex.sub(REDACTED_STRING, record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = redact_sensitive_data(record.args)
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(redact_sensitive_data(arg) for arg in record.args)

        # Sanitize all custom extras attached to the record
        for key in list(record.__dict__.keys()):
            if key in {
                "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
                "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread", "threadName",
                "processName", "process", "message",
            }:
                continue
            if is_sensitive_key(key):
                setattr(record, key, REDACTED_STRING)
            else:
                val = getattr(record, key)
                setattr(record, key, redact_sensitive_data(val))

        return True


class StructuredJsonFormatter(logging.Formatter):
    """
    JSON log formatter producing consistent structured lines with standard identifiers:
    timestamp, level, logger, message, event, job_id, account_id, execution_generation, runner_id.
    """

    STANDARD_ATTRS = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "message",
    }

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()

        message = record.message
        if isinstance(message, str):
            message = redact_sensitive_data(message)

        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "event": getattr(record, "event", "log_entry"),
            "job_id": getattr(record, "job_id", None),
            "account_id": getattr(record, "account_id", None),
            "execution_generation": getattr(record, "execution_generation", None),
            "runner_id": getattr(record, "runner_id", None),
        }

        # Include additional context attributes
        extra_ctx = {}
        for key, val in record.__dict__.items():
            if key not in self.STANDARD_ATTRS and key not in payload:
                extra_ctx[key] = val

        if extra_ctx:
            payload["context"] = redact_sensitive_data(extra_ctx)

        if record.exc_info:
            payload["exception"] = redact_sensitive_data(self.formatException(record.exc_info))

        return json.dumps(payload, default=str)


def log_structured(
    logger: logging.Logger,
    level: int,
    event: str,
    message: str,
    *,
    job_id: Optional[Any] = None,
    account_id: Optional[Any] = None,
    execution_generation: Optional[Any] = None,
    runner_id: Optional[Any] = None,
    **extra: Any,
) -> None:
    """
    Emit a structured log message with standardized identifiers and secret redaction.
    """
    clean_extra = redact_sensitive_data(extra)
    clean_extra.update({
        "event": event,
        "job_id": str(job_id) if job_id is not None else None,
        "account_id": int(account_id) if account_id is not None else None,
        "execution_generation": (
            int(execution_generation) if execution_generation is not None else None
        ),
        "runner_id": str(runner_id) if runner_id is not None else None,
    })
    logger.log(level, message, extra=clean_extra)

