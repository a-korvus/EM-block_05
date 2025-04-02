"""Some routes."""

import asyncio
import logging

from fastapi import APIRouter
from fastapi.responses import ORJSONResponse, Response
from starlette import status

from app.db.query import all_rows, run_check
from app.scraper.main import main as scrap_main
from app.utils.types import session_depends

router = APIRouter()
lgr = logging.getLogger(__name__)


@router.get("/health/", status_code=status.HTTP_200_OK, tags=["health check"])
async def health_check() -> dict:
    """
    Use it endpoint to health check.

    Returns:
        dict: {"status": "ok"} if the service is running.
    """
    return {"status": "ok"}


@router.get("/check-db/", status_code=status.HTTP_200_OK, tags=["database"])
async def check_db() -> dict:
    """Check the state of the database."""
    return await run_check()


@router.get("/start-scrap/", tags=["scraper"])
async def start_scrap(session: session_depends) -> Response:
    """
    Run scrap data. If data already exists, text to user about it.

    Args:
        session (session_depends): Async sqlalchemy session.

    Returns:
        Response: Response from server.
    """
    rows_in_table: int = await all_rows(session)

    if rows_in_table == -1:
        content = {"message": "Migration needs to be done."}
        status_code = status.HTTP_404_NOT_FOUND
    else:
        asyncio.create_task(scrap_main())
        content = {"message": "The scraper is running."}
        status_code = status.HTTP_201_CREATED

    return ORJSONResponse(content, status_code)
