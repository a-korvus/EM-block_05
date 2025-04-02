"""Config data."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class PGConfig(BaseSettings):
    """Postgres config."""

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    PG_HOST: str = "localhost"
    PG_PORT: int = 5432
    PG_DB_NAME: str = "mydb"
    PG_USER: str = "user"
    PG_PASSWORD: str = "password"

    @property
    def url_async(self) -> str:
        """Config a link to postgres connection for asyncpg."""
        # postgresql+asyncpg://postgres:postgres@localhost:5432/db_name
        return (
            "postgresql+asyncpg://"
            f"{self.PG_USER}:{self.PG_PASSWORD}@"
            f"{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB_NAME}"
        )


class RedisConfig(BaseSettings):
    """Redis config."""

    REDIS_USER: str = "user"
    REDIS_USER_PASSWORD: str = "password"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    REDIS_CACHE_DB: int = 0
    REDIS_CELERY_BROKER_DB: int = 1
    REDIS_CELERY_BACKEND_DB: int = 2

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    def _create_url(self, db_num: int) -> str:
        """
        Create a link to redis connection.

        Args:
            host (str): Host to connection.
            db_num (int): Indicate the database number.

        Returns:
            str: URL to connection.
        """
        # redis://username:password@localhost:6379/0
        return (
            f"redis://{self.REDIS_USER}:{self.REDIS_USER_PASSWORD}@"
            f"{self.REDIS_HOST}:{self.REDIS_PORT}/{db_num}"
        )

    @property
    def url_cache(self) -> str:
        """Config a link to caching redis connection."""
        return self._create_url(db_num=self.REDIS_CACHE_DB)

    @property
    def url_celery_broker(self) -> str:
        """Config a link to celery broker redis connection."""
        return self._create_url(db_num=self.REDIS_CELERY_BROKER_DB)

    @property
    def url_celery_backend(self) -> str:
        """Config a link to celery backend redis connection."""
        return self._create_url(db_num=self.REDIS_CELERY_BACKEND_DB)


pg_config = PGConfig()
redis_config = RedisConfig()
