# app/core/redis.py
import redis.asyncio as aioredis
from app.core.config import settings

redis_client: aioredis.Redis = aioredis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
    max_connections=20,
)


async def get_cached(key: str) -> str | None:
    return await redis_client.get(key)


async def set_cached(key: str, value: str, ttl: int = 300) -> None:
    await redis_client.setex(key, ttl, value)


async def delete_cached(key: str) -> None:
    await redis_client.delete(key)


async def delete_pattern(pattern: str) -> None:
    """Delete all keys matching a pattern (e.g., 'products:*')."""
    keys = await redis_client.keys(pattern)
    if keys:
        await redis_client.delete(*keys)
