import hashlib
from typing import Any, Callable

from fastapi_cache.decorator import cache

from app.core.config import redis
from app.core.settings import CACHE_ENABLED

CACHE_PREFIX = "fastapi-cache"

# Per-request dependencies that must never end up in the cache key.
# The SQLAlchemy AsyncSession (injected as `db`) has a different memory
# address on every request, so including it (as the default key builder
# does via repr()) would make the cache miss on every single call.
_EXCLUDED_CACHE_KWARGS = {"db", "request", "response"}


def cache_key_builder(
    func: Callable[..., Any],
    namespace: str = "",
    args: tuple = (),
    kwargs: dict | None = None,
    **_: Any,
) -> str:
    # `namespace` here is already `f"{FastAPICache.get_prefix()}:{namespace}"`
    # (see fastapi_cache.decorator.cache), i.e. it already includes CACHE_PREFIX.
    # Don't prepend CACHE_PREFIX again or the key won't match `clear_cache`'s scan pattern.
    kwargs = kwargs or {}
    filtered_kwargs = {k: v for k, v in kwargs.items() if k not in _EXCLUDED_CACHE_KWARGS}
    key_data = f"{func.__module__}:{func.__name__}:{args}:{filtered_kwargs}"
    return f"{namespace}:{hashlib.md5(key_data.encode()).hexdigest()}"


def cached(*, expire: int, namespace: str) -> Callable:
    """
    Thin wrapper around `fastapi_cache.decorator.cache` that always uses
    `cache_key_builder` and can be globally disabled via the `CACHE_ENABLED`
    setting (env var `CACHE_ENABLED=false`) to A/B compare with/without caching.
    """
    def decorator(func: Callable) -> Callable:
        if not CACHE_ENABLED:
            return func
        return cache(expire=expire, namespace=namespace, key_builder=cache_key_builder)(func)
    return decorator


async def clear_cache(namespace: str) -> None:
    """
    Delete every cached entry under the given namespace directly via Redis.

    Uses the shared `redis` client instead of `FastAPICache.clear()`, so it
    works both from FastAPI request handlers and from Celery workers (which
    never call `FastAPICache.init()`).
    """
    pattern = f"{CACHE_PREFIX}:{namespace}:*"
    keys = [key async for key in redis.scan_iter(match=pattern)]
    if keys:
        await redis.delete(*keys)
