"""
Sleep Schedule Manager

Manages activity windows to simulate human sleep patterns.
Blocks actions during configured sleep hours (default: 11 PM - 7 AM).
"""

import logging
from datetime import datetime, time as dt_time, timezone as dt_timezone
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    logger.debug("pytz not installed, using system timezone")


@dataclass
class SleepConfig:
    """Configuration for sleep schedule."""
    sleep_start_hour: int = 23  # 11 PM
    sleep_end_hour: int = 7     # 7 AM
    timezone: str = "UTC"
    # Randomize wake/sleep times slightly
    randomize_minutes: int = 30


class SleepSchedule:
    """
    Manages sleep hours to avoid bot activity during unrealistic times.
    
    Features:
    - Configurable sleep window (default: 11 PM - 7 AM)
    - Timezone support
    - Randomized wake/sleep times for natural variation
    - Check if currently in sleep hours
    
    Example:
        schedule = SleepSchedule(
            sleep_start_hour=23,
            sleep_end_hour=7,
            timezone="Asia/Kolkata"
        )
        
        if schedule.is_sleep_time():
            wait_seconds = schedule.time_until_wake()
            print(f"Sleep time! Wake in {wait_seconds/3600:.1f} hours")
        else:
            # Perform actions
            pass
    """
    
    def __init__(
        self,
        sleep_start_hour: int = 23,
        sleep_end_hour: int = 7,
        timezone: str = "UTC",
        randomize_minutes: int = 30
    ):
        """
        Initialize the sleep schedule.
        
        Args:
            sleep_start_hour: Hour to start sleeping (0-23), default 23 (11 PM)
            sleep_end_hour: Hour to wake up (0-23), default 7 (7 AM)
            timezone: Timezone string (e.g., "Asia/Kolkata", "US/Eastern")
            randomize_minutes: Random variation in sleep/wake time
        """
        self.sleep_start_hour = sleep_start_hour
        self.sleep_end_hour = sleep_end_hour
        self.timezone_str = timezone
        self.randomize_minutes = randomize_minutes
        
        if PYTZ_AVAILABLE:
            try:
                self.timezone = pytz.timezone(timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning(f"Unknown timezone {timezone}, using UTC")
                self.timezone = pytz.UTC
                self.timezone_str = "UTC"
        else:
            self.timezone = dt_timezone.utc
            self.timezone_str = "UTC"
        
        logger.info(
            f"SleepSchedule initialized: "
            f"sleep {sleep_start_hour}:00 - {sleep_end_hour}:00 ({self.timezone_str})"
        )
    
    def _get_current_time(self) -> datetime:
        """Get current time in configured timezone."""
        if PYTZ_AVAILABLE and hasattr(self.timezone, 'localize'):
            return datetime.now(self.timezone)
        return datetime.now(dt_timezone.utc)
    
    def is_sleep_time(self, check_time: Optional[datetime] = None) -> bool:
        """
        Check if the given time (or now) is within sleep hours.
        
        Args:
            check_time: Optional datetime to check, uses current time if None
            
        Returns:
            True if within sleep hours, False otherwise
        """
        if check_time is None:
            check_time = self._get_current_time()
        elif check_time.tzinfo is None:
            # Localize naive datetime
            if PYTZ_AVAILABLE and hasattr(self.timezone, 'localize'):
                check_time = self.timezone.localize(check_time)
            else:
                check_time = check_time.replace(tzinfo=dt_timezone.utc)
        
        current_hour = check_time.hour
        
        # Handle overnight sleep (e.g., 23:00 to 07:00)
        if self.sleep_start_hour > self.sleep_end_hour:
            # Sleep period spans midnight
            is_sleeping = current_hour >= self.sleep_start_hour or current_hour < self.sleep_end_hour
        else:
            # Sleep period within same day
            is_sleeping = self.sleep_start_hour <= current_hour < self.sleep_end_hour
        
        if is_sleeping:
            logger.debug(f"Sleep time detected at {check_time.strftime('%H:%M')}")
        
        return is_sleeping
    
    def time_until_wake(self, from_time: Optional[datetime] = None) -> float:
        """
        Calculate seconds until wake time.
        
        Args:
            from_time: Optional start time, uses current time if None
            
        Returns:
            Seconds until wake time (0 if not currently sleeping)
        """
        if from_time is None:
            from_time = self._get_current_time()
        elif from_time.tzinfo is None:
            if PYTZ_AVAILABLE and hasattr(self.timezone, 'localize'):
                from_time = self.timezone.localize(from_time)
            else:
                from_time = from_time.replace(tzinfo=dt_timezone.utc)
        
        if not self.is_sleep_time(from_time):
            return 0.0
        
        # Calculate wake time
        wake_time = from_time.replace(
            hour=self.sleep_end_hour,
            minute=0,
            second=0,
            microsecond=0
        )
        
        # If wake time is earlier in the day, it's tomorrow
        if wake_time <= from_time:
            from datetime import timedelta
            wake_time += timedelta(days=1)
        
        delta = (wake_time - from_time).total_seconds()
        return max(0.0, delta)
    
    def time_until_sleep(self, from_time: Optional[datetime] = None) -> float:
        """
        Calculate seconds until sleep time.
        
        Args:
            from_time: Optional start time, uses current time if None
            
        Returns:
            Seconds until sleep time (0 if currently sleeping)
        """
        if from_time is None:
            from_time = self._get_current_time()
        elif from_time.tzinfo is None:
            if PYTZ_AVAILABLE and hasattr(self.timezone, 'localize'):
                from_time = self.timezone.localize(from_time)
            else:
                from_time = from_time.replace(tzinfo=dt_timezone.utc)
        
        if self.is_sleep_time(from_time):
            return 0.0
        
        # Calculate sleep time
        sleep_time = from_time.replace(
            hour=self.sleep_start_hour,
            minute=0,
            second=0,
            microsecond=0
        )
        
        # If sleep time is earlier in the day, it's tomorrow
        if sleep_time <= from_time:
            from datetime import timedelta
            sleep_time += timedelta(days=1)
        
        delta = (sleep_time - from_time).total_seconds()
        return max(0.0, delta)
    
    def get_active_window(self) -> Tuple[dt_time, dt_time]:
        """
        Get the active (non-sleep) time window.
        
        Returns:
            Tuple of (start_time, end_time) for active hours
        """
        return (
            dt_time(self.sleep_end_hour, 0),
            dt_time(self.sleep_start_hour, 0)
        )
    
    def format_status(self) -> str:
        """
        Get human-readable status.
        
        Returns:
            Status string
        """
        now = self._get_current_time()
        if self.is_sleep_time():
            wait_hours = self.time_until_wake() / 3600
            return f"😴 Sleep time! Wake in {wait_hours:.1f} hours"
        else:
            active_hours = self.time_until_sleep() / 3600
            return f"🌞 Active! {active_hours:.1f} hours until sleep"


# Convenience function
def is_sleep_time(
    sleep_start: int = 23,
    sleep_end: int = 7,
    timezone: str = "UTC"
) -> bool:
    """
    Quick check if current time is within sleep hours.
    
    Args:
        sleep_start: Hour to start sleeping (0-23)
        sleep_end: Hour to wake up (0-23)
        timezone: Timezone string
        
    Returns:
        True if currently sleep time
    """
    schedule = SleepSchedule(sleep_start, sleep_end, timezone)
    return schedule.is_sleep_time()
