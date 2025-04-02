"""Caching tools."""

import logging
from typing import Any

import orjson
import redis.asyncio as aioredis
from redis.asyncio.client import Redis

from app.config import redis_config

lgr = logging.getLogger(__name__)

redis_client_cache: Redis = aioredis.from_url(
    url=redis_config.url_cache,
    decode_responses=False,
    health_check_interval=10,
)


def serialize(value: Any) -> bytes:
    """
    Serialize some value from python type to bytes.

    Args:
        value (Any): Any serializable python value.

    Returns:
        bytes: Serialized object.

    Raises:
        TypeError: If the value isn't serializable.
    """
    try:
        serialized: bytes = orjson.dumps(value)
    except TypeError as e:
        lgr.error(f"Key {value} is incorrect.", exc_info=e)
        raise e
    return serialized


async def get_cache_data(key: Any) -> Any:
    """
    Get data from cache by the key.

    Args:
        key (Any): Some serializable key value.

    Returns:
        Any: Cached value.
    """
    key = serialize(key)
    data = await redis_client_cache.get(key)

    log_message = f"Get and return cache for key '{key}'"
    if not data:
        log_message = f"No cache for key '{key}'"
    lgr.info(log_message)
    return orjson.loads(data) if data else None


async def set_cache_data(key: Any, value: Any, expire: int = 86400) -> None:
    """
    Set data to cache by the key.

    Args:
        key (Any): Some serializable key value.
        value (Any): Some serializable value to cache.
        expire (int, optional): Seconds before key expires.
            Defaults to 86400 (24h).
    """
    key = serialize(key)
    value = serialize(value)
    await redis_client_cache.set(name=key, value=value, ex=expire)
    lgr.info(f"Set cache for '{key}' for {expire} seconds.")
