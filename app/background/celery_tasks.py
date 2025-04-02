"""Celery background tasks in the FastAPI app."""

import logging
from datetime import datetime, timezone

from celery import shared_task
from redis import Redis

from app.config import redis_config

lgr = logging.getLogger(__name__)


@shared_task(name="app.background.celery_tasks.reset_cache")
def reset_cache() -> None:
    """Clear all cache data in redis. Async function."""
    redis_client: Redis = Redis.from_url(redis_config.url_cache)

    try:
        result = redis_client.flushdb()

        now_utc: str = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H:%M:%S")
        log_msg = f"Cache has been flushed at {now_utc}"
        if not result:
            log_msg = f"Cache hasn't been flushed at {now_utc}"
        lgr.info(log_msg)
    finally:
        redis_client.close()
