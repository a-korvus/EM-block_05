"""Main router in the FastAPI app."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from starlette import status

from app.db.models import Result as ResultModel
from app.db.query import (
    q_get_dynamics,
    q_get_last_trading_dates,
    q_get_trading_results,
)
from app.db.schemas import ResultSchemaOutput
from app.utils.caching import get_cache_data, set_cache_data
from app.utils.types import default_days, now_date_query, session_depends

router = APIRouter(prefix="/api", tags=["api"])
lgr = logging.getLogger(__name__)


@router.get("/get-last-trading-dates/", status_code=status.HTTP_200_OK)
async def get_last_trading_dates(
    session: session_depends,
    days: int = default_days,
) -> list[str]:
    """
    List of dates of the last trading days.

    Apply filtering by number of the last trading days.

    Args:
        session (session_depends): Async sqlalchemy session.
        days (int, optional): Number of last trading days.
            Defaults to Query(default=1, ge=1).

    Returns:
        list: _description_
    """
    cache_key: str = f"last_tr_dt_{days}"
    cached_data: list[str] | None = await get_cache_data(cache_key)

    if cached_data:
        return cached_data

    query_result: list[str] = await q_get_last_trading_dates(
        session=session,
        days=days,
    )
    await set_cache_data(key=cache_key, value=query_result)
    return query_result


@router.get("/get-dynamics/", status_code=status.HTTP_200_OK)
async def get_dynamics(
    session: session_depends,
    oil_id: str,
    delivery_type_id: str,
    delivery_basis_id: str,
    start_date: now_date_query,
    end_date: now_date_query,
) -> list[dict]:
    """
    List of trades for a given period. Filter by query parameters.

    Args:
        session (session_depends): Async sqlalchemy session.
        oil_id (str): Trade parameter.
        delivery_type_id (str): Trade parameter.
        delivery_basis_id (str): Trade parameter.
        start_date (now_date_query): Trade parameter.
        end_date (now_date_query): Trade parameter.

    Raises:
        HTTPException: If the entered dates are incorrect.

    Returns:
        list[dict]: Filtered result.
    """
    try:
        start: datetime = datetime.strptime(start_date, "%Y-%m-%d")
        end: datetime = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"{e}"
        )

    cache_key: str = (
        f"dynamics_{oil_id}_{delivery_type_id}_{delivery_basis_id}_"
        f"{start_date}_{end_date}"
    )
    cached_data: list[dict] | None = await get_cache_data(cache_key)

    if cached_data:
        return cached_data

    list_models: list[ResultModel] = await q_get_dynamics(
        session=session,
        oil_id=oil_id,
        delivery_type_id=delivery_type_id,
        delivery_basis_id=delivery_basis_id,
        start_date=start,
        end_date=end,
    )
    query_result = [
        ResultSchemaOutput.model_validate(model).model_dump()
        for model in list_models
    ]

    await set_cache_data(key=cache_key, value=query_result)

    return query_result


@router.get("/get-trading-results/", status_code=status.HTTP_200_OK)
async def get_trading_results(
    session: session_depends,
    oil_id: str | None = None,
    delivery_type_id: str | None = None,
    delivery_basis_id: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """
    List of last trades. Filter by query parameters.

    Args:
        session (session_depends): Async sqlalchemy session.
        oil_id (str): Trade parameter.
        delivery_type_id (str): Trade parameter.
        delivery_basis_id (str): Trade parameter.
        limit (int): Quantity limit.

    Raises:
        HTTPException: If not conditions or limit isn't positive number.

    Returns:
        list[dict]: Filtered result.
    """
    if not any((oil_id, delivery_type_id, delivery_basis_id)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="At least one of the trading parameters must be filled in.",
        )
    if limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The limit must be a positive number.",
        )

    cache_key: str = (
        f"trade_results_{oil_id or "-"}_{delivery_type_id or "-"}_"
        f"{delivery_basis_id or "-"}_{limit}"
    )
    cached_data: list[dict] | None = await get_cache_data(cache_key)

    if cached_data:
        return cached_data

    list_models: list[ResultModel] = await q_get_trading_results(
        session=session,
        oil_id=oil_id,
        delivery_type_id=delivery_type_id,
        delivery_basis_id=delivery_basis_id,
        limit=limit,
    )

    query_result = [
        ResultSchemaOutput.model_validate(model).model_dump()
        for model in list_models
    ]
    await set_cache_data(key=cache_key, value=query_result)

    return query_result
