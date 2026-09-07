"""Async Redis client for caching and rate-limiting."""

import redis.asyncio as aioredis

from app.config import get_settings

_settings = get_settings()

redis_client: aioredis.Redis = aioredis.from_url(  # type: ignore[assignment]
    _settings.REDIS_URL,
    decode_responses=True,
)


async def get_redis() -> aioredis.Redis:  # type: ignore[type-arg]
    """FastAPI dependency returning the shared Redis client."""
    return redis_client
