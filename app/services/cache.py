import json
from typing import Any, Optional

import redis.asyncio as aioredis

from app.config import settings

redis_client: Optional[aioredis.Redis] = None


async def init_cache():
    global redis_client
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def close_cache():
    global redis_client
    if redis_client:
        await redis_client.close()


async def cache_get(key: str) -> Any | None:
    if not redis_client:
        return None
    val = await redis_client.get(key)
    return json.loads(val) if val else None


async def cache_set(key: str, value: Any, ttl: int = 60):
    if not redis_client:
        return
    await redis_client.setex(key, ttl, json.dumps(value))


async def cache_delete(key: str):
    if not redis_client:
        return
    await redis_client.delete(key)
