"""Main database settings."""

from typing import Any, AsyncGenerator, Callable, Coroutine

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import pg_config

async_engine: AsyncEngine = create_async_engine(
    url=pg_config.url_async,
    echo=False,
    pool_size=5,
    max_overflow=10,
)

async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
)


async def run_pg_session(
    func: Callable[..., Coroutine[Any, Any, Any]],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Open the async session for further operations.

    Use it function as a wrapper for other functions
    that do something with the database.

    Args:
        func (Callable[..., Coroutine[Any, Any, Any]]): Asynchronous function
        that contains some logic for interacting with the database.
        *args (Any): Positional arguments to be passed to the function.
        **kwargs (Any): Keyword arguments to be passed to the function.
    """
    async with async_session() as session:
        kwargs["session"] = session
        return await func(*args, **kwargs)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides aa asynchronous SQLAlchemy database session.

    Yields:
        AsyncSession: SQLAlchemy AsyncSession instance for database operations.
    """
    async with async_session() as session:
        yield session
