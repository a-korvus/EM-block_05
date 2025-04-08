"""
Setup test DB.

An independent engine is created to perform test environment setup.
"""

import asyncio
import logging
import os

from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import text

from app.config import pg_config
from app.db.models import Base
from tests.utils import configure_logging

lgr = logging.getLogger(__name__)

ADMIN_DB_URL = (
    f"postgresql+asyncpg://{pg_config.PG_USER}:{pg_config.PG_PASSWORD}@"
    f"localhost:5432/{pg_config.PG_DB_NAME}"
)
TEST_DB_NAME = os.getenv("PG_TEST_DB_NAME", "my_test_db")
TEST_DB_USER = os.getenv("PG_TEST_USER", "test_user")
TEST_DB_PASSWORD = os.getenv("PG_TEST_PASSWORD", "test_password")
TEST_DB_URL = (
    f"postgresql+asyncpg://{TEST_DB_USER}:{TEST_DB_PASSWORD}@"
    f"localhost:5432/{TEST_DB_NAME}"
)


async def create_test_db_and_user(
    admin_connection_url: str, test_db: str, test_user: str, test_password: str
) -> None:
    """
    Connect to PostgreSQL and create test db and test user.

    Use existing credentials. Dispose of the engine after completing work.
    """
    # движок от имени администратора для создания тестовой среды
    engine = create_async_engine(
        admin_connection_url,
        isolation_level="AUTOCOMMIT",
    )

    async with engine.connect() as conn:
        try:
            # проверить/создать тестового пользователя
            user_exists = await conn.execute(
                text("SELECT 1 FROM pg_roles WHERE rolname = :user"),
                {"user": test_user},
            )
            if not user_exists.scalar_one_or_none():
                lgr.info(f"Creating test user '{test_user}'")
                # идентификаторы нельзя параметризовать :param
                create_user_sql = text(
                    f'CREATE USER "{test_user}" '
                    f"WITH PASSWORD '{test_password}'"
                )
                await conn.execute(create_user_sql)
                lgr.info(f"User '{test_user}' created")
            else:
                lgr.info(f"Test user '{test_user}' already exists")

            # проверить/создать тестовую базу данных
            db_exists = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": test_db},
            )
            if not db_exists.scalar_one_or_none():
                lgr.info(f"Creating test DB '{test_db}'")
                # Устанавливаем владельцем нового пользователя
                await conn.execute(
                    text(f'CREATE DATABASE "{test_db}" OWNER "{test_user}"')
                )
                lgr.info(f"Database '{test_db}' created")
            else:
                lgr.info(f"Database '{test_db}' already exists")

            # выдать права test_user на БД, даже если она уже есть
            # нужно, если БД была создана ранее другим способом
            lgr.info(f"Grant privileges on '{test_db}' to '{test_user}'")
            await conn.execute(
                text(
                    f'GRANT ALL PRIVILEGES ON DATABASE "{test_db}" '
                    f'TO "{test_user}"'
                )
            )
            lgr.info(f"Privileges to '{test_user}' on '{test_db}' granted")

        except ProgrammingError as e:
            lgr.error(f"SQL error while setting up test db/user: {e}")
            raise RuntimeError(f"Failed to configure test DB/user: {e}") from e
        except Exception as e:
            lgr.error(f"Unexpected error while setting up test DB: {e}")
            raise RuntimeError(f"Failed to configure test DB/user: {e}") from e
        finally:
            await engine.dispose()


async def setup_db_before_tests() -> None:
    """
    Run creating test DB and test user.

    Raises:
        RuntimeError: Exceptions raised during setup.
    """
    lgr.info("Start setup_environment_for_tests")
    try:
        await create_test_db_and_user(
            admin_connection_url=ADMIN_DB_URL,
            test_db=TEST_DB_NAME,
            test_user=TEST_DB_USER,
            test_password=TEST_DB_PASSWORD,
        )
        lgr.info("Test environment done")
        lgr.info(f"URL to connect to the test DB: {TEST_DB_URL}")
        test_engine = create_async_engine(url=TEST_DB_URL)

        # выполняем create_all асинхронно
        async with test_engine.begin() as conn:
            lgr.info("Creating tables in the test DB.")
            # запускаем синхронный create_all через run_sync
            # метод create_all работает с объектом MetaData,
            # поэтому остается синхронным
            await conn.run_sync(Base.metadata.create_all)
            lgr.info("All tables has been created in the test DB")

        lgr.info("The test environment setup has been completed successfully")
        # тут можно вернуть движок дальше для фикстур сессии, если нужно
        # return test_engine
    except RuntimeError as e:
        lgr.exception(f"Error setting up test environment:\n{e}\n")
        raise e
    finally:
        # очищаем ресурсы движка тестовой БД, если он был создан
        if test_engine:
            await test_engine.dispose()
            lgr.info("Setup test engine released.")


async def cleanup_test_environment(
    admin_connection_url: str,
    test_db: str,
    test_user: str,
) -> None:
    """Cleanup all test environment."""
    lgr.info(
        "Run test environment cleanup. "
        f"Test DB: {test_db}; test user: {test_user}"
    )
    # создаем движок от админ пользователя, не тест
    engine = create_async_engine(
        admin_connection_url,
        isolation_level="AUTOCOMMIT",
    )

    async with engine.connect() as conn:
        try:
            lgr.info(f"Terminating active sessions to DB '{test_db}'")
            # завершить все активные подключения к БД, за исключением текущего
            # иначе невозможно удалить БД с актиынми подключениями
            terminate_sessions_sql = text(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE datname = :db_name AND pid <> pg_backend_pid()"
            )
            await conn.execute(terminate_sessions_sql, {"db_name": test_db})
            lgr.info(f"Active sessions to DB '{test_db}' have ended")

            lgr.info(f"Dropping the test database '{test_db}'")
            drop_db_sql = text(f'DROP DATABASE IF EXISTS "{test_db}"')
            await conn.execute(drop_db_sql)
            lgr.info(f"Database '{test_db}' has been dropped")

            lgr.info(f"Dropping the test user '{test_user}'")
            drop_user_sql = text(f'DROP USER IF EXISTS "{test_user}"')
            await conn.execute(drop_user_sql)
            lgr.info(f"User '{test_user}' has been dropped")

        except ProgrammingError as e:
            # ошибки могут возникать, если объект уже удален,
            # это нормально для cleanup
            lgr.warning(f"Just log SQL error while cleanup:\n{e}\n")
            pass
        except DBAPIError as e:
            # ошибки уровня DBAPI, например, проблемы с соединением
            lgr.exception(f"DBAPI error while cleanup:\n{e}\n")
            raise RuntimeError(
                f"Cleanup failed due to DBAPI error: {e}"
            ) from e
        except Exception as e:
            lgr.exception(f"Unexpected error while cleanup:\n{e}\n")
            raise RuntimeError(
                f"Cleanup failed due to unexpected error:\n{e}\n"
            ) from e
        finally:
            await engine.dispose()
            lgr.info("Admin cleaning engine released.")


async def teardown_db_after_tests() -> None:
    """
    Call test environment cleanup.

    Raises:
        RuntimeError: Exception occurred while cleanup the test environment.
    """
    lgr.info("Starting test environment cleanup after tests.")
    try:
        await cleanup_test_environment(
            admin_connection_url=ADMIN_DB_URL,
            test_db=TEST_DB_NAME,
            test_user=TEST_DB_USER,
        )
        lgr.info("Cleanup test environment done.")
    except RuntimeError as e:
        lgr.exception(f"Error while cleanup test environment:\n{e}\n")
        raise e


async def main() -> None:
    await setup_db_before_tests()
    print("\n>>> The test environment is set up, you can run tests <<<\n")
    # предполагается, что тут выполняются тесты
    input("\nPress any key\n")
    await teardown_db_after_tests()


if __name__ == "__main__":
    configure_logging(level=logging.DEBUG)
    asyncio.run(main())
