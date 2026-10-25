"""
clock.py — Demo clock service providing settable "now" for test scenarios.

RULES:
- Every module and date calculation MUST import now() or today() from here.
- Never call datetime.now() directly in business logic.
- Evaluators can fast-forward time to test 180D/90D/60D/30D/7D alerts.
"""

from datetime import date, datetime, timezone, timedelta
import os

_override_dt: datetime | None = None

# Check environment override at startup if specified
_env_override = os.getenv("DEMO_CLOCK_OVERRIDE")
if _env_override:
    try:
        _override_dt = datetime.fromisoformat(_env_override.rstrip("Z")).replace(tzinfo=timezone.utc)
    except Exception:
        pass


class Clock:
    """System time provider with dynamic time-travel capabilities for demo evaluation."""

    @classmethod
    def now(cls) -> datetime:
        """Return current time (or simulated demo override)."""
        global _override_dt
        if _override_dt is not None:
            return _override_dt
        return datetime.now(timezone.utc)

    @classmethod
    def today(cls) -> date:
        """Return current date."""
        return cls.now().date()

    @classmethod
    def set_override(cls, target_dt: datetime | str) -> None:
        """Set simulated clock time."""
        global _override_dt
        if isinstance(target_dt, str):
            _override_dt = datetime.fromisoformat(target_dt.rstrip("Z")).replace(tzinfo=timezone.utc)
        else:
            if target_dt.tzinfo is None:
                _override_dt = target_dt.replace(tzinfo=timezone.utc)
            else:
                _override_dt = target_dt

    @classmethod
    def advance_days(cls, days: int) -> datetime:
        """Advance the simulated clock by N days."""
        global _override_dt
        current = cls.now()
        _override_dt = current + timedelta(days=days)
        return _override_dt

    @classmethod
    def clear_override(cls) -> None:
        """Reset back to real system clock."""
        global _override_dt
        _override_dt = None

    @classmethod
    def is_simulated(cls) -> bool:
        """Return True if time is currently overridden."""
        return _override_dt is not None
