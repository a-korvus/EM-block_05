"""
Some tests to check how DB related tools works.

Using test database.
"""

import pytest
from pytest_mock import MockerFixture
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Result
from app.db.query import create_data
from app.db.schemas import ResultSchema
from tests.utils import fake_result, fake_result_many


def test_accept_input_data() -> None:
    """Check how accept and validate the input data."""
    input_result: dict = fake_result()
    input_result["delivery_type_id"] = input_result["delivery_type_id"] + "A"

    with pytest.raises(ValueError):
        ResultSchema(**input_result)

    input_result["delivery_type_id"] = input_result["delivery_type_id"][:1]
    schema = ResultSchema(**input_result)

    for field_name in input_result:
        assert input_result[field_name] == getattr(schema, field_name)


def test_create_model() -> None:
    """Check how creating the Result model and saving to DB."""
    input_result = fake_result()
    schema = ResultSchema(**input_result)
    model = Result(**schema.model_dump())

    assert isinstance(model, Result)
    for field_name in input_result:
        assert input_result[field_name] == getattr(model, field_name)


@pytest.mark.anyio
async def test_add_and_query_data(db_session: AsyncSession) -> None:
    """
    Create a Result instance and query it from the database.

    Args:
        db_session (AsyncSession): Fixture that yields an async session.
    """
    input_result: dict = fake_result()
    schema = ResultSchema(**input_result)
    model = Result(**schema.model_dump())

    db_session.add(model)
    await db_session.flush()
    # flush() - отправляем изменения в базу данных ВНУТРИ транзакции
    await db_session.refresh(model)

    assert isinstance(model.id, int)

    stmt = select(Result).where(Result.id == model.id)
    result = await db_session.execute(stmt)
    queried_record = result.scalar_one_or_none()

    assert isinstance(queried_record, Result)
    for field_name, value in input_result.items():
        assert value == getattr(queried_record, field_name)


@pytest.mark.anyio
async def test_add_many(raw_db_session: AsyncSession) -> None:
    """
    Create a many Result instance and query it from the database.

    Args:
        raw_db_session (AsyncSession): Fixture that yields an async session.
    """
    input_data: list[list[dict]] = fake_result_many()
    num_input_rows: int = sum(len(inner_lst) for inner_lst in input_data)

    await create_data(data=input_data, session=raw_db_session)

    result = await raw_db_session.execute(select(Result))
    all_results = result.scalars().all()

    assert num_input_rows == len(all_results)


@pytest.mark.anyio
async def test_single_commit(mocker: MockerFixture) -> None:
    """
    Make sure the session calls one commit and adds the correct models.

    Args:
        mocker (MockerFixture): Fixture to creating mocks.
    """
    input_data: list[list[dict]] = fake_result_many()
    num_input_files: int = len(input_data)
    num_input_rows: int = sum(len(inner_lst) for inner_lst in input_data)

    # spec=AsyncSession, чтобы мок имел атрибуты реальной сессии
    mock_session = mocker.AsyncMock(spec=AsyncSession)
    mock_session.add_all = mocker.MagicMock()
    mock_session.commit = mocker.AsyncMock()

    await create_data(data=input_data, session=mock_session)

    mock_session.commit.assert_awaited_once()
    assert mock_session.add_all.call_count == num_input_files

    added_models = []
    for mock_call in mock_session.add_all.call_args_list:
        # call_args_list содержит кортежи (args, kwargs)
        # args[0] - список моделей, переданный в add_all оригинальной сессии
        args, _ = mock_call

        assert isinstance(args[0], list)

        added_models.extend(args[0])

    assert num_input_rows == len(added_models)
    assert all(isinstance(model, Result) for model in added_models)
