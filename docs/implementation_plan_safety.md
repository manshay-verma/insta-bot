# Safety Module - Implementation Plan

Implement the Safety Module with a **clean, well-organized structure** following Python best practices.

## Proposed Directory Structure

```
automation/safety/
├── __init__.py              # Package exports
├── rate_limiter/
│   ├── __init__.py
│   ├── base.py              # Abstract rate limiter interface
│   ├── memory_limiter.py    # In-memory rate limiting (default)
│   └── redis_limiter.py     # Redis-backed rate limiting (optional)
├── behavior/
│   ├── __init__.py
│   ├── delays.py            # Random delay generator
│   ├── scheduler.py         # Sleep hours logic
│   └── warmup.py            # New account warmup protocol
├── risk/
│   ├── __init__.py
│   ├── health_tracker.py    # Account health score
│   ├── detection.py         # Warning/ban signal detection
│   └── action_logger.py     # Audit logging
├── config.py                # Centralized safety config
└── safety_manager.py        # Main orchestrator class
```

### Test Structure
```
automation/safety/
└── tests/
    ├── __init__.py
    ├── test_rate_limiter.py
    ├── test_behavior.py
    └── test_risk.py
```

---

## Proposed Changes

### Phase 1: Core Infrastructure

#### [NEW] `automation/safety/__init__.py`
Main package exports for easy imports:
```python
from .safety_manager import SafetyManager
from .config import SafetyConfig
```

#### [NEW] `automation/safety/config.py`
Centralized configuration with sensible defaults:
```python
@dataclass
class SafetyConfig:
    # Rate limits
    actions_per_hour: int = 60
    actions_per_day: int = 500
    
    # Delays (seconds)
    min_delay: float = 15.0
    max_delay: float = 45.0
    
    # Sleep hours (24h format)
    sleep_start_hour: int = 23  # 11 PM
    sleep_end_hour: int = 7     # 7 AM
    
    # Redis (optional)
    redis_url: Optional[str] = None
```

---

### Phase 2: Rate Limiting (Tasks 1-4)

#### [NEW] `automation/safety/rate_limiter/base.py`
Abstract interface:
```python
class RateLimiter(ABC):
    @abstractmethod
    def can_perform(action_type: str) -> bool: ...
    
    @abstractmethod
    def record_action(action_type: str) -> None: ...
    
    @abstractmethod
    def get_remaining(action_type: str) -> dict: ...
```

#### [NEW] `automation/safety/rate_limiter/memory_limiter.py`
Default in-memory implementation using sliding windows.

#### [NEW] `automation/safety/rate_limiter/redis_limiter.py`
Optional Redis-backed implementation for distributed systems.

---

### Phase 3: Human Behavior (Tasks 5-8)

#### [NEW] `automation/safety/behavior/delays.py`
```python
async def random_delay(min_sec=15, max_sec=45) -> None
def jitter(base_delay: float, variance: float = 0.3) -> float
```

#### [NEW] `automation/safety/behavior/scheduler.py`
```python
def is_sleep_time(hour: int, config: SafetyConfig) -> bool
async def wait_until_active() -> None
```

#### [NEW] `automation/safety/behavior/warmup.py`
Gradual limit increases for new accounts.

---

### Phase 4: Risk Management (Tasks 9-12)

#### [NEW] `automation/safety/risk/health_tracker.py`
Track account health via success/failure ratios.

#### [NEW] `automation/safety/risk/detection.py`
Detect warning signals (rate limit responses, CAPTCHA, etc.)

#### [NEW] `automation/safety/risk/action_logger.py`
Structured logging for auditing all actions.

---

### Phase 5: Main Orchestrator

#### [NEW] `automation/safety/safety_manager.py`
```python
class SafetyManager:
    """Central coordinator for all safety features."""
    
    def __init__(self, config: SafetyConfig = None):
        self.config = config or SafetyConfig()
        self.rate_limiter = MemoryRateLimiter(config)
        self.health_tracker = HealthTracker()
        self.action_logger = ActionLogger()
    
    async def before_action(self, action_type: str) -> bool:
        """Check if action is safe to perform."""
        
    async def after_action(self, action_type: str, success: bool):
        """Record result and update metrics."""
```

---

## Verification Plan

### Automated Tests
Create unit tests in `automation/safety/tests/`:

```bash
python -m pytest automation/safety/tests/ -v
```

| Test File | Coverage |
|-----------|----------|
| `test_rate_limiter.py` | Memory + Redis limiters, per-hour/day limits |
| `test_behavior.py` | Delay ranges, sleep hour detection |
| `test_risk.py` | Health score calculation, detection logic |

### Manual Verification
After implementation, verify integration with Playwright:
1. Import SafetyManager in browser_manager.py
2. Test rate limiting by running multiple actions
3. Verify delays between actions are applied

---

## Implementation Order

1. **config.py** + **safety_manager.py** (skeleton)
2. **rate_limiter/** (Tasks 1-4)
3. **behavior/** (Tasks 5-8)
4. **risk/** (Tasks 9-12)
5. Tests for each phase
6. Integration with Playwright module
