"""Main Celery settings."""

from celery import Celery
from celery.schedules import crontab

import app.background.celery_tasks  # noqa
from app.config import redis_config

celery_app = Celery(
    __name__,
    broker=redis_config.url_celery_broker,
    backend=redis_config.url_celery_backend,
    broker_connection_retry_on_startup=True,
    worker_hijack_root_logger=False,
)

celery_app.conf.beat_schedule = {
    "reset_cache_at_14_11": {
        "task": "app.background.celery_tasks.reset_cache",
        "schedule": crontab(hour="14", minute="11"),  # каждый день в 14:11
        "options": {
            "expires": 300  # истекает через 5 мин после времени запуска
        },
    }
}
