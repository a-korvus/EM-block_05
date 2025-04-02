"""Some useful tools."""

from datetime import datetime, timezone


def now_utc() -> str:
    """Get current UTC time."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
