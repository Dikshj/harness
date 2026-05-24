
import json
import redis.asyncio as redis
from harness.config import get_settings

settings = get_settings()
_pool = None
_memory_cache = {}

def _get_pool():
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(settings.redis_url)
    return _pool

async def get_redis():
    return redis.Redis(connection_pool=_get_pool())

async def set_json(key: str, value, ttl: int = 3600):
    try:
        r = await get_redis()
        await r.setex(key, ttl, json.dumps(value))
    except Exception:
        _memory_cache[key] = value

async def get_json(key: str):
    try:
        r = await get_redis()
        raw = await r.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return _memory_cache.get(key)
