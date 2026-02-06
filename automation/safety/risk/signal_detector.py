"""
Warning/Ban Signal Detector

Detects warning signs from Instagram that may indicate account issues:
- Rate limiting responses
- Unusual captcha/verification requests
- Action blocks
- Suspicious activity warnings
"""

import re
import logging
from datetime import datetime
from typing import List, Optional, Dict, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Types of warning signals."""
    RATE_LIMIT = "rate_limit"
    ACTION_BLOCK = "action_block"
    CAPTCHA = "captcha"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    PHONE_VERIFICATION = "phone_verification"
    EMAIL_VERIFICATION = "email_verification"
    TEMPORARY_BAN = "temporary_ban"
    PERMANENT_BAN = "permanent_ban"
    LOGOUT_FORCED = "logout_forced"
    UNKNOWN = "unknown"


class SignalSeverity(Enum):
    """Severity levels for signals."""
    LOW = 1       # Minor issue, continue with caution
    MEDIUM = 2    # Slow down significantly
    HIGH = 3      # Stop for a while
    CRITICAL = 4  # Stop immediately, manual review needed


@dataclass
class WarningSignal:
    """Represents a detected warning signal."""
    signal_type: SignalType
    severity: SignalSeverity
    message: str
    source: str  # Where the signal was detected (URL, response body, etc.)
    timestamp: datetime = field(default_factory=datetime.now)
    raw_data: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "signal_type": self.signal_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "raw_data": self.raw_data
        }


class SignalDetector:
    """
    Detects warning and ban signals from Instagram.
    
    Features:
    - Pattern matching on responses
    - URL-based detection
    - HTTP status code analysis
    - Custom detector registration
    
    Example:
        detector = SignalDetector()
        
        # Check a response
        signals = detector.detect_from_response(
            status_code=429,
            body="Please wait a few minutes",
            url="https://www.instagram.com/api/v1/likes/"
        )
        
        for signal in signals:
            if signal.severity == SignalSeverity.CRITICAL:
                print(f"CRITICAL: {signal.message}")
    """
    
    # Known warning patterns in responses
    RESPONSE_PATTERNS = {
        SignalType.RATE_LIMIT: [
            r"please wait.*minutes",
            r"try again later",
            r"too many requests",
            r"rate.?limit",
            r"slow down",
        ],
        SignalType.ACTION_BLOCK: [
            r"action blocked",
            r"we restrict certain activity",
            r"you're temporarily blocked",
            r"this action was blocked",
            r"temporarily blocked from performing",
        ],
        SignalType.CAPTCHA: [
            r"verify.*human",
            r"captcha",
            r"recaptcha",
            r"security check",
            r"prove you're not a robot",
        ],
        SignalType.SUSPICIOUS_ACTIVITY: [
            r"suspicious activity",
            r"unusual activity",
            r"we've detected",
            r"your account.*security",
            r"something went wrong",
        ],
        SignalType.PHONE_VERIFICATION: [
            r"confirm.*phone",
            r"verify.*phone",
            r"add.*phone number",
            r"phone verification",
        ],
        SignalType.EMAIL_VERIFICATION: [
            r"confirm.*email",
            r"verify.*email",
            r"check.*email",
        ],
        SignalType.TEMPORARY_BAN: [
            r"temporarily disabled",
            r"your account has been suspended",
            r"temporarily locked",
            r"account is temporarily",
        ],
        SignalType.PERMANENT_BAN: [
            r"permanently disabled",
            r"your account has been disabled",
            r"violates.*terms",
            r"account has been removed",
        ],
        SignalType.LOGOUT_FORCED: [
            r"session expired",
            r"please log in again",
            r"you've been logged out",
        ],
    }
    
    # URL patterns that indicate issues
    URL_PATTERNS = {
        SignalType.ACTION_BLOCK: [
            r"challenge",
            r"blocked",
        ],
        SignalType.PHONE_VERIFICATION: [
            r"checkpoint.*phone",
            r"verify.*phone",
        ],
        SignalType.CAPTCHA: [
            r"captcha",
            r"challenge",
        ],
    }
    
    # HTTP status codes
    STATUS_SIGNALS = {
        429: (SignalType.RATE_LIMIT, SignalSeverity.HIGH),
        401: (SignalType.LOGOUT_FORCED, SignalSeverity.HIGH),
        403: (SignalType.ACTION_BLOCK, SignalSeverity.HIGH),
    }
    
    def __init__(self):
        """Initialize the signal detector."""
        # Compile patterns for efficiency
        self._response_patterns: Dict[SignalType, List[re.Pattern]] = {}
        for signal_type, patterns in self.RESPONSE_PATTERNS.items():
            self._response_patterns[signal_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        
        self._url_patterns: Dict[SignalType, List[re.Pattern]] = {}
        for signal_type, patterns in self.URL_PATTERNS.items():
            self._url_patterns[signal_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        
        # Custom detectors (callable returns Optional[WarningSignal])
        self._custom_detectors: List[Callable] = []
        
        # History of detected signals
        self._signal_history: List[WarningSignal] = []
        
        logger.info("SignalDetector initialized")
    
    def detect_from_response(
        self,
        body: str = "",
        status_code: int = 200,
        url: str = "",
        headers: Optional[Dict] = None
    ) -> List[WarningSignal]:
        """
        Detect warning signals from an HTTP response.
        
        Args:
            body: Response body text
            status_code: HTTP status code
            url: Request URL
            headers: Response headers
            
        Returns:
            List of detected warning signals
        """
        signals = []
        
        # Check status code
        if status_code in self.STATUS_SIGNALS:
            signal_type, severity = self.STATUS_SIGNALS[status_code]
            signals.append(WarningSignal(
                signal_type=signal_type,
                severity=severity,
                message=f"HTTP {status_code} response",
                source=f"status_code:{url}",
                raw_data={"status_code": status_code}
            ))
        
        # Check response body patterns
        body_lower = body.lower()
        for signal_type, patterns in self._response_patterns.items():
            for pattern in patterns:
                match = pattern.search(body_lower)
                if match:
                    severity = self._get_severity_for_type(signal_type)
                    signals.append(WarningSignal(
                        signal_type=signal_type,
                        severity=severity,
                        message=f"Pattern matched: '{match.group()}'",
                        source=f"response_body:{url}",
                        raw_data={"matched": match.group(), "pattern": pattern.pattern}
                    ))
                    break  # One match per type is enough
        
        # Check URL patterns
        for signal_type, patterns in self._url_patterns.items():
            for pattern in patterns:
                if pattern.search(url):
                    severity = self._get_severity_for_type(signal_type)
                    signals.append(WarningSignal(
                        signal_type=signal_type,
                        severity=severity,
                        message=f"Suspicious URL pattern detected",
                        source=f"url:{url}",
                        raw_data={"url": url, "pattern": pattern.pattern}
                    ))
                    break
        
        # Check rate limit headers
        if headers:
            if headers.get("x-ratelimit-remaining") == "0":
                signals.append(WarningSignal(
                    signal_type=SignalType.RATE_LIMIT,
                    severity=SignalSeverity.MEDIUM,
                    message="Rate limit header indicates limit reached",
                    source=f"header:{url}",
                    raw_data={"header": "x-ratelimit-remaining"}
                ))
        
        # Run custom detectors
        for detector in self._custom_detectors:
            try:
                result = detector(body, status_code, url, headers)
                if result:
                    signals.append(result)
            except Exception as e:
                logger.error(f"Custom detector error: {e}")
        
        # Store in history
        self._signal_history.extend(signals)
        
        # Log signals
        for signal in signals:
            log_level = logging.CRITICAL if signal.severity == SignalSeverity.CRITICAL else \
                       logging.ERROR if signal.severity == SignalSeverity.HIGH else \
                       logging.WARNING
            logger.log(log_level, f"Signal detected: {signal.signal_type.value} - {signal.message}")
        
        return signals
    
    def detect_from_page(
        self,
        page_content: str,
        page_url: str
    ) -> List[WarningSignal]:
        """
        Detect signals from a browser page.
        
        Args:
            page_content: HTML content of the page
            page_url: Current page URL
            
        Returns:
            List of detected warning signals
        """
        return self.detect_from_response(
            body=page_content,
            status_code=200,
            url=page_url
        )
    
    def _get_severity_for_type(self, signal_type: SignalType) -> SignalSeverity:
        """Get default severity for a signal type."""
        severity_map = {
            SignalType.RATE_LIMIT: SignalSeverity.MEDIUM,
            SignalType.ACTION_BLOCK: SignalSeverity.HIGH,
            SignalType.CAPTCHA: SignalSeverity.MEDIUM,
            SignalType.SUSPICIOUS_ACTIVITY: SignalSeverity.HIGH,
            SignalType.PHONE_VERIFICATION: SignalSeverity.HIGH,
            SignalType.EMAIL_VERIFICATION: SignalSeverity.MEDIUM,
            SignalType.TEMPORARY_BAN: SignalSeverity.CRITICAL,
            SignalType.PERMANENT_BAN: SignalSeverity.CRITICAL,
            SignalType.LOGOUT_FORCED: SignalSeverity.HIGH,
            SignalType.UNKNOWN: SignalSeverity.LOW,
        }
        return severity_map.get(signal_type, SignalSeverity.MEDIUM)
    
    def register_detector(
        self,
        detector: Callable[[str, int, str, Optional[Dict]], Optional[WarningSignal]]
    ) -> None:
        """
        Register a custom signal detector.
        
        Args:
            detector: Callable that takes (body, status_code, url, headers)
                     and returns Optional[WarningSignal]
        """
        self._custom_detectors.append(detector)
        logger.debug("Registered custom signal detector")
    
    def get_recent_signals(
        self,
        limit: int = 50,
        signal_type: Optional[SignalType] = None,
        min_severity: Optional[SignalSeverity] = None
    ) -> List[WarningSignal]:
        """
        Get recent signals from history.
        
        Args:
            limit: Maximum number of signals to return
            signal_type: Filter by signal type
            min_severity: Filter by minimum severity
            
        Returns:
            List of recent signals
        """
        signals = self._signal_history[-limit:]
        
        if signal_type:
            signals = [s for s in signals if s.signal_type == signal_type]
        
        if min_severity:
            signals = [s for s in signals if s.severity.value >= min_severity.value]
        
        return signals
    
    def clear_history(self) -> None:
        """Clear signal history."""
        self._signal_history.clear()
        logger.debug("Cleared signal history")
    
    def has_critical_signals(self, within_hours: int = 1) -> bool:
        """
        Check if there are any critical signals recently.
        
        Args:
            within_hours: Time window to check
            
        Returns:
            True if critical signals detected
        """
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=within_hours)
        
        for signal in reversed(self._signal_history):
            if signal.timestamp < cutoff:
                break
            if signal.severity == SignalSeverity.CRITICAL:
                return True
        
        return False
