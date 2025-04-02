"""Annotated variables in this app."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.setup import get_session
from app.utils.tools import now_utc

session_depends = Annotated[AsyncSession, Depends(get_session)]
default_days: int = Query(default=1, ge=1)
now_date_query = Annotated[
    str, Query(default_factory=now_utc, example="2025-04-01")
]
