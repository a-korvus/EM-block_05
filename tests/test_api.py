"""Some tests to check how API works using pytest."""

import random
from datetime import datetime

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture
from starlette import status

from app.db.models import Result
from app.db.schemas import ResultSchemaOutput
from tests.utils import fake_result_output


@pytest.mark.anyio
async def test_get_last_trading_dates_without_cache(
    httpx_test_client: AsyncClient,
    mocker: MockerFixture,
) -> None:
    """
    Test enpoint 'get_last_trading_dates'.

    Tests the DB call, cache setup, and DB data return.
    Scenario test: data not found in cache.

    Args:
        httpx_test_client (AsyncClient): Test httpx async client.
        mocker (MockerFixture): Fixture to creating mocks.
    """
    test_days = 5
    cache_key = f"last_tr_dt_{test_days}"
    expected_db_result = ["2025-04-08", "2025-04-07", "2025-04-05"]

    # мокируем зависимости
    # важно указывать путь к функции там, где она ИСПОЛЬЗУЕТСЯ (в роутере)
    mock_get_cache = mocker.patch(
        "app.routers.get_data.get_cache_data",
        return_value=None,
        new_callable=mocker.AsyncMock,
    )
    mock_set_cache = mocker.patch(
        "app.routers.get_data.set_cache_data",
        return_value=None,
        new_callable=mocker.AsyncMock,
    )
    mock_db_query = mocker.patch(
        "app.routers.get_data.q_get_last_trading_dates",
        return_value=expected_db_result,
        new_callable=mocker.AsyncMock,
    )

    # запрос к эндпоинту
    response = await httpx_test_client.get(
        f"/api/get-last-trading-dates/?days={test_days}",
    )

    assert status.HTTP_200_OK == response.status_code
    assert expected_db_result == response.json()

    mock_get_cache.assert_awaited_once_with(cache_key)
    mock_set_cache.assert_awaited_once()
    mock_set_cache.assert_awaited_once_with(
        key=cache_key,
        value=expected_db_result,
    )

    _, call_kwargs = mock_db_query.call_args
    assert call_kwargs["days"] == test_days


@pytest.mark.anyio
async def test_get_last_trading_dates_with_cache(
    httpx_test_client: AsyncClient,
    mocker: MockerFixture,
) -> None:
    """
    Test enpoint 'get_last_trading_dates'.

    Tests the DB call, get and return cache.
    Check that DB is not called, cache is not reinstalled.
    Scenario test: data found in cache.

    Args:
        httpx_test_client (AsyncClient): Test httpx async client.
        mocker (MockerFixture): Fixture to creating mocks.
    """
    test_days = 3
    cache_key = f"last_tr_dt_{test_days}"
    expected_cache_result = ["2025-03-25", "2025-03-27"]

    mock_get_cache = mocker.patch(
        "app.routers.get_data.get_cache_data",
        return_value=expected_cache_result,
        new_callable=mocker.AsyncMock,
    )
    mock_set_cache = mocker.patch(
        "app.routers.get_data.set_cache_data",
        new_callable=mocker.AsyncMock,
    )
    mock_db_query = mocker.patch(
        "app.routers.get_data.q_get_last_trading_dates",
        new_callable=mocker.AsyncMock,
    )

    response = await httpx_test_client.get(
        f"/api/get-last-trading-dates/?days={test_days}",
    )

    assert status.HTTP_200_OK == response.status_code
    assert expected_cache_result == response.json()

    mock_get_cache.assert_awaited_once_with(cache_key)
    mock_set_cache.assert_not_awaited()
    mock_db_query.assert_not_awaited()


@pytest.mark.anyio
async def test_get_dynamics_without_cache(
    httpx_test_client: AsyncClient,
    mocker: MockerFixture,
) -> None:
    """
    Test endpoint 'get_dynamics'.

    Tests the DB call, cache setup, and DB data return.
    Scenario test: data not found in cache.

    Args:
        httpx_test_client (AsyncClient): Test httpx async client.
        mocker (MockerFixture): Fixture to creating mocks.
    """
    oil_id = "A"
    delivery_type_id = "B"
    delivery_basis_id = "C"
    start_date = "2025-04-08"
    end_date = "2025-04-06"

    expected_db_result: list[Result] = [
        Result(**fake_result_output()) for _ in range(random.randint(3, 10))
    ]
    expected_db_result_json = [
        ResultSchemaOutput.model_validate(model).model_dump(mode="json")
        for model in expected_db_result
    ]

    cache_key = (
        f"dynamics_{oil_id}_{delivery_type_id}_{delivery_basis_id}_"
        f"{start_date}_{end_date}"
    )
    cahe_result = [
        ResultSchemaOutput.model_validate(model).model_dump()
        for model in expected_db_result
    ]

    mock_get_cache = mocker.patch(
        "app.routers.get_data.get_cache_data",
        return_value=None,
        new_callable=mocker.AsyncMock,
    )
    mock_set_cache = mocker.patch(
        "app.routers.get_data.set_cache_data",
        return_value=None,
        new_callable=mocker.AsyncMock,
    )
    mock_db_query = mocker.patch(
        "app.routers.get_data.q_get_dynamics",
        return_value=expected_db_result,
        new_callable=mocker.AsyncMock,
    )

    response = await httpx_test_client.get(
        f"/api/get-dynamics/?oil_id={oil_id}&"
        f"delivery_type_id={delivery_type_id}&"
        f"delivery_basis_id={delivery_basis_id}&"
        f"start_date={start_date}&end_date={end_date}"
    )

    assert status.HTTP_200_OK == response.status_code
    assert expected_db_result_json == response.json()

    mock_get_cache.assert_awaited_once_with(cache_key)
    mock_set_cache.assert_awaited_once()
    mock_set_cache.assert_awaited_once_with(
        key=cache_key,
        value=cahe_result,
    )

    _, call_kwargs = mock_db_query.call_args
    assert call_kwargs["oil_id"] == oil_id
    assert call_kwargs["delivery_type_id"] == delivery_type_id
    assert call_kwargs["delivery_basis_id"] == delivery_basis_id
    assert call_kwargs["start_date"] == datetime.strptime(
        start_date,
        "%Y-%m-%d",
    )
    assert call_kwargs["end_date"] == datetime.strptime(end_date, "%Y-%m-%d")


@pytest.mark.anyio
async def test_get_dynamics_with_cache(
    httpx_test_client: AsyncClient,
    mocker: MockerFixture,
) -> None:
    """
    Test endpoint 'get_dynamics'.

    Tests the DB call, get and return cache.
    Check that DB is not called, cache is not reinstalled.
    Scenario test: data found in cache.

    Args:
        httpx_test_client (AsyncClient): Test httpx async client.
        mocker (MockerFixture): Fixture to creating mocks.
    """
    oil_id = "A"
    delivery_type_id = "B"
    delivery_basis_id = "C"
    start_date = "2025-04-08"
    end_date = "2025-04-06"

    cache_key = (
        f"dynamics_{oil_id}_{delivery_type_id}_{delivery_basis_id}_"
        f"{start_date}_{end_date}"
    )
    cahe_result_json = [
        ResultSchemaOutput.model_validate(model).model_dump(mode="json")
        for model in [
            Result(**fake_result_output())
            for _ in range(random.randint(3, 10))
        ]
    ]

    mock_get_cache = mocker.patch(
        "app.routers.get_data.get_cache_data",
        return_value=cahe_result_json,
        new_callable=mocker.AsyncMock,
    )
    mock_set_cache = mocker.patch(
        "app.routers.get_data.set_cache_data",
        new_callable=mocker.AsyncMock,
    )
    mock_db_query = mocker.patch(
        "app.routers.get_data.q_get_dynamics",
        new_callable=mocker.AsyncMock,
    )

    response = await httpx_test_client.get(
        f"/api/get-dynamics/?oil_id={oil_id}&"
        f"delivery_type_id={delivery_type_id}&"
        f"delivery_basis_id={delivery_basis_id}&"
        f"start_date={start_date}&end_date={end_date}"
    )

    assert status.HTTP_200_OK == response.status_code
    assert cahe_result_json == response.json()

    mock_get_cache.assert_awaited_once_with(cache_key)
    mock_set_cache.assert_not_awaited()
    mock_db_query.assert_not_awaited()


@pytest.mark.anyio
async def test_get_trading_results_without_cache(
    httpx_test_client: AsyncClient,
    mocker: MockerFixture,
) -> None:
    """
    Test endpoint 'get_dynamics'.

    Tests the DB call, cache setup, and DB data return.
    Scenario test: data not found in cache.

    Args:
        httpx_test_client (AsyncClient): Test httpx async client.
        mocker (MockerFixture): Fixture to creating mocks.
    """
    oil_id = "A"
    delivery_type_id = "B"
    delivery_basis_id = "C"
    limit = 3

    expected_db_result: list[Result] = [
        Result(**fake_result_output()) for _ in range(limit)
    ]
    expected_db_result_json = [
        ResultSchemaOutput.model_validate(model).model_dump(mode="json")
        for model in expected_db_result
    ]

    cache_key: str = (
        f"trade_results_{oil_id or "-"}_{delivery_type_id or "-"}_"
        f"{delivery_basis_id or "-"}_{limit}"
    )
    cahe_result = [
        ResultSchemaOutput.model_validate(model).model_dump()
        for model in expected_db_result
    ]

    mock_get_cache = mocker.patch(
        "app.routers.get_data.get_cache_data",
        return_value=None,
        new_callable=mocker.AsyncMock,
    )
    mock_set_cache = mocker.patch(
        "app.routers.get_data.set_cache_data",
        return_value=None,
        new_callable=mocker.AsyncMock,
    )
    mock_db_query = mocker.patch(
        "app.routers.get_data.q_get_trading_results",
        return_value=expected_db_result,
        new_callable=mocker.AsyncMock,
    )

    response = await httpx_test_client.get(
        f"/api/get-trading-results/?oil_id={oil_id}&"
        f"delivery_type_id={delivery_type_id}&"
        f"delivery_basis_id={delivery_basis_id}&limit={limit}"
    )

    assert status.HTTP_200_OK == response.status_code
    assert expected_db_result_json == response.json()

    mock_get_cache.assert_awaited_once_with(cache_key)
    mock_set_cache.assert_awaited_once()
    mock_set_cache.assert_awaited_once_with(
        key=cache_key,
        value=cahe_result,
    )

    _, call_kwargs = mock_db_query.call_args
    assert call_kwargs["oil_id"] == oil_id
    assert call_kwargs["delivery_type_id"] == delivery_type_id
    assert call_kwargs["delivery_basis_id"] == delivery_basis_id
    assert call_kwargs["limit"] == limit


@pytest.mark.anyio
async def test_get_trading_results_with_cache(
    httpx_test_client: AsyncClient,
    mocker: MockerFixture,
) -> None:
    """
    Test endpoint 'get_trading_results'.

    Tests the DB call, get and return cache.
    Check that DB is not called, cache is not reinstalled.
    Scenario test: data found in cache.

    Args:
        httpx_test_client (AsyncClient): Test httpx async client.
        mocker (MockerFixture): Fixture to creating mocks.
    """
    oil_id = "A"
    delivery_type_id = "B"
    delivery_basis_id = "C"
    limit = 3

    cache_key: str = (
        f"trade_results_{oil_id or "-"}_{delivery_type_id or "-"}_"
        f"{delivery_basis_id or "-"}_{limit}"
    )
    cahe_result_json = [
        ResultSchemaOutput.model_validate(model).model_dump(mode="json")
        for model in [Result(**fake_result_output()) for _ in range(limit)]
    ]

    mock_get_cache = mocker.patch(
        "app.routers.get_data.get_cache_data",
        return_value=cahe_result_json,
        new_callable=mocker.AsyncMock,
    )
    mock_set_cache = mocker.patch(
        "app.routers.get_data.set_cache_data",
        new_callable=mocker.AsyncMock,
    )
    mock_db_query = mocker.patch(
        "app.routers.get_data.q_get_trading_results",
        new_callable=mocker.AsyncMock,
    )

    response = await httpx_test_client.get(
        f"/api/get-trading-results/?oil_id={oil_id}&"
        f"delivery_type_id={delivery_type_id}&"
        f"delivery_basis_id={delivery_basis_id}&limit={limit}"
    )

    assert status.HTTP_200_OK == response.status_code
    assert cahe_result_json == response.json()

    mock_get_cache.assert_awaited_once_with(cache_key)
    mock_set_cache.assert_not_awaited()
    mock_db_query.assert_not_awaited()
