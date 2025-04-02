"""Some db queries."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Result as ResultModel
from app.db.schemas import ResultSchema
from app.db.setup import run_pg_session

lgr = logging.getLogger(__name__)


async def check_pg_version(session: AsyncSession) -> str:
    """Check DB connection. Show postgres version."""
    result: Result[Any] = await session.execute(
        statement=text("SELECT version();"),
    )

    version = result.scalar_one()
    lgr.info(version)

    return version


async def all_rows(session: AsyncSession) -> int:
    """Show the number of rows in the Result table."""

    def check_table(sync_session: Any) -> bool:
        """Check if table exists. Synchronous helper."""
        bind = sync_session.get_bind()
        from sqlalchemy import inspect

        inspector = inspect(bind)
        return inspector.has_table(ResultModel.__tablename__)

    table_exists = await session.run_sync(check_table)
    if not table_exists:
        log = f"Table '{ResultModel.__tablename__}' doesn't exist."
        response = -1
    else:
        stmt = select(func.count(ResultModel.id))
        result = await session.execute(stmt)
        rows = result.scalar_one()
        log = f"Result table contains {rows} rows."
        response = rows

    lgr.info(log)
    return response


async def run_check() -> dict:
    """Check pg version and table Result state."""
    version = await run_pg_session(check_pg_version)
    rows = await run_pg_session(all_rows)

    return {"version": version, "rows": rows}


async def create_data(data: list[list[dict]], session: AsyncSession) -> None:
    """Process all parsed data and save it to db."""
    lgr.info("Start saving data to db.")
    for file_data in data:
        res_schs = [ResultSchema(**rows) for rows in file_data]
        models = [ResultModel(**result.model_dump()) for result in res_schs]

        session.add_all(models)

    await session.commit()
    lgr.info("Data have been saved to db.")


async def get_last_date(session: AsyncSession) -> datetime | None:
    """
    Get the last date of trading results from database.

    Args:
        session (AsyncSession): Async sqlalchemy session.

    Returns:
        datetime | None: The last trading date that has been parsed.
            None if results table is empty.
    """
    stmt = (
        select(ResultModel.date)
        .distinct()
        .order_by(ResultModel.date.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def q_get_last_trading_dates(
    session: AsyncSession,
    days: int,
) -> list[str]:
    """
    Get dates of the last trading days.

    Args:
        session (AsyncSession): Async sqlalchemy session.
        days (int): Number of the trading days.

    Returns:
        list[str]: The last dates.
    """
    stmt = (
        select(ResultModel.date)
        .distinct()
        .order_by(ResultModel.date.desc())
        .limit(days)
    )
    result = await session.execute(stmt)
    list_result = result.scalars().all()

    return [trade_date.strftime("%Y-%m-%d") for trade_date in list_result]


async def q_get_dynamics(
    session: AsyncSession,
    oil_id: str,
    delivery_type_id: str,
    delivery_basis_id: str,
    start_date: datetime,
    end_date: datetime,
) -> list[ResultModel]:
    """
    Get list of trades for a given period. Filter by trade parameters.

    Args:
        session (AsyncSession): Async sqlalchemy session.
        oil_id (str): Trade parameter.
        delivery_type_id (str): Trade parameter.
        delivery_basis_id (str): Trade parameter.
        start_date (datetime): Trade parameter.
        end_date (datetime): Trade parameter.

    Returns:
        list[ResultModel]: Filtered result.
    """
    stmnt = select(ResultModel).filter(
        ResultModel.oil_id == oil_id,
        ResultModel.delivery_type_id == delivery_type_id,
        ResultModel.delivery_basis_id == delivery_basis_id,
        ResultModel.date.between(start_date, end_date),
    )
    result = await session.execute(stmnt)
    return list(result.scalars().all())


async def q_get_trading_results(
    session: AsyncSession,
    oil_id: str | None,
    delivery_type_id: str | None,
    delivery_basis_id: str | None,
    limit: int,
) -> list[ResultModel]:
    """
    Get list of last trades. Filter by trade parameters.

    Args:
        session (AsyncSession): Async sqlalchemy session.
        oil_id (str): Trade parameter.
        delivery_type_id (str): Trade parameter.
        delivery_basis_id (str): Trade parameter.
        limit (int): Quantity limit.

    Returns:
        list[ResultModel]: Filtered result.
    """
    conditions: list = []
    if oil_id:
        conditions.append(ResultModel.oil_id == oil_id)
    if delivery_type_id:
        conditions.append(ResultModel.delivery_type_id == delivery_type_id)
    if delivery_basis_id:
        conditions.append(ResultModel.delivery_basis_id == delivery_basis_id)

    stmnt = (
        select(ResultModel)
        .filter(*conditions)
        .order_by(ResultModel.date.desc())
        .limit(limit)
    )
    result = await session.execute(stmnt)
    return list(result.scalars().all())


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(lineno)d | %(asctime)s | %(name)s | "
        "%(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    try:
        asyncio.run(run_check())
    except OSError:
        lgr.error("Unable to establish connection to database")
