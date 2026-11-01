import hashlib
from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from app.constants import CACHE_PREFIX, EXCLUDED_CACHE_KWARGS, GLOBAL_SCOPE
from app.core.config import redis
from app.core.settings import get_settings
from app.enums import CacheNamespace

settings = get_settings()


def _index_key(entry_key: str) -> str:
    return f"{entry_key.rsplit(':', 1)[0]}:index"


class IndexedRedisBackend(RedisBackend):
    """Also records each key in a set per namespace and scope, so `clear_cache` can delete
    a user's entries without scanning the keyspace."""

    async def set(self, key: str, value: bytes, expire: int | None = None) -> None:
        index = _index_key(key)
        async with self.redis.pipeline(transaction=False) as pipe:
            pipe.set(key, value, ex=expire)
            pipe.sadd(index, key)
            # Every entry in a namespace shares one TTL, so the set outlives its members.
            if expire:
                pipe.expire(index, expire)
            await pipe.execute()


def cache_key_builder(
    func: Callable[..., Any],
    namespace: str = "",
    args: tuple = (),
    kwargs: dict | None = None,
    **_: Any,
) -> str:
    # `namespace` already includes CACHE_PREFIX (fastapi_cache.decorator.cache adds it);
    # prepending it again breaks the layout `clear_cache` relies on.
    kwargs = kwargs or {}
    filtered_kwargs = {k: v for k, v in kwargs.items() if k not in EXCLUDED_CACHE_KWARGS}
    key_data = f"{func.__module__}:{func.__name__}:{args}:{filtered_kwargs}"
    # Outside the digest so each user's keys share one index set.
    scope = kwargs.get("user_id") or GLOBAL_SCOPE
    # A cache-key digest, not a security primitive.
    digest = hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()
    return f"{namespace}:{scope}:{digest}"


def cached(*, expire: int, namespace: CacheNamespace) -> Callable:
    """`fastapi_cache`'s `cache` with `cache_key_builder`, or a no-op when caching is disabled."""

    def decorator(func: Callable) -> Callable:
        if not settings.cache_enabled:
            return func
        return cache(expire=expire, namespace=namespace, key_builder=cache_key_builder)(func)

    return decorator


async def clear_cache(namespace: CacheNamespace, user_id: UUID | str | None = None) -> None:
    """`user_id` scopes the cleanup; omitting it clears the namespace for every user.

    Uses the shared `redis` client rather than `FastAPICache.clear()`, so it also works from
    Celery workers, which never call `FastAPICache.init()`.
    """
    if user_id is None:
        pattern = f"{CACHE_PREFIX}:{namespace}:*"
        keys = [key async for key in redis.scan_iter(match=pattern, count=1000)]
    else:
        index = _index_key(f"{CACHE_PREFIX}:{namespace}:{user_id}:")
        keys = [index, *await redis.smembers(index)]
    if keys:
        await redis.delete(*keys)
