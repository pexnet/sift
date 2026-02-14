from functools import lru_cache

from redis import Redis
from rq import Queue

from sift.config import get_settings


@lru_cache
def get_redis_connection() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url)


@lru_cache
def get_ingest_queue() -> Queue:
    settings = get_settings()
    return Queue(settings.ingest_queue_name, connection=get_redis_connection())

