"""Pytest configuration settings."""

import logging
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.main import app
from tests.setup_db import (
    TEST_DB_URL,
    setup_db_before_tests,
    teardown_db_after_tests,
)
from tests.utils import configure_logging

lgr = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Integrate anyio into pytest."""
    return "asyncio"


@pytest.fixture(scope="session")
async def db_engine_generator() -> AsyncGenerator[AsyncEngine, None]:
    """
    Manage the test database engine at the session level.

    1. Run custom setup method;
    2. Yields the SQLAlchemy test engine connected to the test database;
    3. Run custom teardown method.

    Returns:
        AsyncGenerator[AsyncEngine, None]: Main test engine.
    """
    test_engine: AsyncEngine | None = None
    try:
        await setup_db_before_tests()
        test_engine = create_async_engine(url=TEST_DB_URL)

        yield test_engine

    except Exception as e:  # noqa
        lgr.exception(f"Critical error while setting up test db:\n{e}\n")
        pytest.fail(f"Failed to configure test DB:\n{e}\n")
        if test_engine:
            await test_engine.dispose()

        lgr.info("Try to clean up after failed setup")
        try:
            await teardown_db_after_tests()
        except Exception as cleanup_e:  # noqa
            lgr.exception(
                "Error when trying to clean after unsuccessful setup "
                f"test environment:\n{cleanup_e}\n"
            )
        raise  # исходная ошибка настройки

    finally:
        # очистка после всех тестов; выполняется после yield
        if test_engine:
            lgr.info("Start freeing up test engine resources")
            await test_engine.dispose()
            lgr.info("Engine resources have been released")

        try:
            await teardown_db_after_tests()
        except Exception as e:  # noqa
            # лог ошибки очистки, но не проваливаем тестовую сессию
            lgr.exception(f"Error while teardown after tests:\n{e}\n")
            pass


@pytest.fixture(scope="session")
async def db_engine(
    db_engine_generator: AsyncGenerator[AsyncEngine, None],
) -> AsyncEngine:
    """
    Return the AsyncEngine object obtained from the async generator.

    Args:
        db_engine_generator (AsyncGenerator[AsyncEngine, None]):
            AsyncEngine object from generator.

    Returns:
        AsyncEngine: Test AsyncEngine object.
    """
    lgr.debug(f"Get AsyncEngine object from generator: {db_engine_generator}")

    if not isinstance(db_engine_generator, AsyncEngine):
        lgr.error(f"'db_engine' get wrong type: {type(db_engine_generator)}")
        pytest.fail(
            "'db_engine' fixture expected AsyncEngine, "
            f"got {type(db_engine_generator)}"
        )
    return db_engine_generator


@pytest.fixture(scope="function", autouse=True)
async def truncate_tables(
    db_engine: AsyncEngine,
) -> AsyncGenerator[None, None]:
    """
    Clear tables before each test.

    Explicitly gets the result of the db_engine fixture via request.
    """
    lgr.info("Start clearing tables (truncate) before test")
    if not isinstance(db_engine, AsyncEngine):
        lgr.error(
            "WRONG type in 'truncate_tables': db_engine is "
            f"'{type(db_engine)}'"
        )
        pytest.fail(
            "Error in 'truncate_tables': was expected AsyncEngine, "
            f"received '{type(db_engine)}'"
        )

    try:
        async with db_engine.begin() as conn:
            lgr.info(f"Run TRUNCATE on engine '{db_engine}'")
            await conn.execute(
                text("TRUNCATE TABLE spimex_trading_results RESTART IDENTITY")
            )
            # тут можно добавить TRUNCATE для других таблиц, если необходимо
        lgr.info("Table truncation before test completed")

        yield  # выполнение теста

    except Exception as e:  # noqa
        lgr.exception(f"Error while truncation tables: {e}")
        pytest.fail(f"Error while truncation tables: {e}")


@pytest.fixture(scope="function")
async def db_session(
    db_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Manage at the test db session at the function level.

    1. Accepts the db_engine engine (created once per session earler).
    2. Creates a session factory.
    3. Creates a session and starts a nested transaction.
    4. Yields the session to the tests.
    5. Rolls back the transaction after the test completes.

    Args:
        db_engine (AsyncEngine): Test db engine.

    Yields:
        AsyncGenerator[AsyncSession, None]: Main test session.
    """
    if not isinstance(db_engine, AsyncEngine):
        lgr.error(
            f"WRONG type in 'db_session': db_engine is '{type(db_engine)}'"
        )
        pytest.fail(
            "Error in 'db_session': was expected AsyncEngine, "
            f"received '{type(db_engine)}'"
        )

    async_session_maker = async_sessionmaker(
        bind=db_engine,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        lgr.debug(f"Test session '{session}' created for test")
        # вложенная транзакция автоматически откатится при выходе из
        # внутреннего with, если не было commit
        async with session.begin_nested():
            lgr.debug(
                f"Nested transaction (SAVEPOINT) started for '{session}'"
            )
            yield session
        lgr.debug(
            f"Nested transaction (SAVEPOINT) finished for '{session}'; "
            "implicit rollback"
        )
    lgr.debug(f"Test session '{session}' closed")


@pytest.fixture(scope="function")
async def raw_db_session(
    db_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Get the raw AsyncSession without transaction management.

    Args:
        db_engine (AsyncEngine): Test db engine.

    Yields:
        AsyncSession: Async session.
    """
    async_session_maker = async_sessionmaker(
        bind=db_engine,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        lgr.debug(f"Raw session '{session}' created")
        try:
            yield session
        finally:
            lgr.debug(f"Raw session '{session}' closed")


@pytest.fixture(scope="function")
async def httpx_test_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Provide a client for http requests.

    Yields:
        Iterator[AsyncGenerator[AsyncClient, None]]: Test httpx async client.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


configure_logging(level=logging.DEBUG)
