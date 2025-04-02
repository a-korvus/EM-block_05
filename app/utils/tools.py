"""Some useful tools."""

from asyncio import Event
from datetime import datetime, timezone

scrap_event = Event()


def now_utc() -> str:
    """Get current UTC time."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
