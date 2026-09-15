"""Shared synchronous Redis connection for API admission and Celery workers."""

from functools import lru_cache
from redis import Redis
from redis.retry import Retry
from redis.backoff import ExponentialBackoff

from core.config import get_settings


@lru_cache(maxsize=1)
def get_redis() -> Redis:
    """Create a Redis client with short timeouts for queue control."""
    settings = get_settings()
    return Redis.from_url(
        settings.redis_url,
        decode_responses=False,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry=Retry(ExponentialBackoff(cap=10, base=1), retries=3),
        retry_on_timeout=True,
        retry_on_error=[ConnectionError, TimeoutError, OSError],
    )
