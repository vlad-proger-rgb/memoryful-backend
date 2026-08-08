import hashlib
from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi_cache.decorator import cache

from app.constants import CACHE_PREFIX, EXCLUDED_CACHE_KWARGS, GLOBAL_SCOPE
from app.core.config import redis
from app.core.settings import get_settings

settings = get_settings()


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
    filtered_kwargs = {k: v for k, v in kwargs.items() if k not in EXCLUDED_CACHE_KWARGS}
    key_data = f"{func.__module__}:{func.__name__}:{args}:{filtered_kwargs}"
    # Outside the digest so `clear_cache` can scan by user.
    scope = kwargs.get("user_id") or GLOBAL_SCOPE
    # A cache-key digest, not a security primitive.
    digest = hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()
    return f"{namespace}:{scope}:{digest}"


def cached(*, expire: int, namespace: str) -> Callable:
    """
    Thin wrapper around `fastapi_cache.decorator.cache` that always uses
    `cache_key_builder` and can be globally disabled via the `CACHE_ENABLED`
    setting (env var `CACHE_ENABLED=false`) to A/B compare with/without caching.
    """

    def decorator(func: Callable) -> Callable:
        if not settings.cache_enabled:
            return func
        return cache(expire=expire, namespace=namespace, key_builder=cache_key_builder)(func)

    return decorator


async def clear_cache(namespace: str, user_id: UUID | str | None = None) -> None:
    """
    Delete cached entries under the given namespace directly via Redis.

    `user_id` scopes the cleanup to one user; omitting it clears the whole namespace.

    Uses the shared `redis` client instead of `FastAPICache.clear()`, so it
    works both from FastAPI request handlers and from Celery workers (which
    never call `FastAPICache.init()`).
    """
    scope = user_id if user_id is not None else "*"
    pattern = f"{CACHE_PREFIX}:{namespace}:{scope}:*"
    keys = [key async for key in redis.scan_iter(match=pattern)]
    if keys:
        await redis.delete(*keys)
