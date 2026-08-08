import asyncio
import logging
import sys
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from sqlalchemy import select

sys.path.append("..")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Set specific logger for AI operations to be more verbose
ai_logger = logging.getLogger("app.ai")
ai_logger.setLevel(logging.DEBUG)

from app.ai.catalog import sync_chat_models
from app.constants import CACHE_PREFIX
from app.core.config import cache_redis
from app.core.database import AsyncSessionLocal
from app.core.exceptions import register_exception_handlers
from app.core.settings import get_settings
from app.init_db import init_db
from app.models import User
from app.routers import (
    ai,
    auth,
    cities,
    countries,
    days,
    email,
    insights,
    months,
    storage,
    suggestions,
    tags,
    trackable_types,
    trackables,
    workspaces,
)
from app.schemas import Msg

settings = get_settings()


async def run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    def _upgrade() -> None:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _upgrade)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    FastAPICache.init(RedisBackend(cache_redis), prefix=CACHE_PREFIX)

    if settings.trusted_emails:
        logging.warning(
            "Login verification is bypassed for %d address(es) (ENVIRONMENT=%s)",
            len(settings.trusted_emails),
            settings.environment,
        )

    # await run_migrations()
    async with AsyncSessionLocal() as session:
        # Reference data: kept in sync in every environment, but never fatal —
        # a catalog sync failure (e.g. the DB is behind on migrations during a
        # deploy) must not take down the whole API.
        try:
            await sync_chat_models(session)
        except Exception:
            logging.exception("Chat model catalog sync failed; continuing startup")
            await session.rollback()
        if settings.is_development and settings.seed_db_on_empty:
            has_any_user = await session.scalar(select(User.id).limit(1))
            if not has_any_user:
                await init_db(session)
    yield


app = FastAPI(
    title="Memoryful API",
    description="Backend API for Memoryful",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=settings.allow_credentials,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
)


@app.middleware("http")
async def disable_http_caching(request: Request, call_next: Callable) -> Response:
    """
    fastapi_cache's `cache` decorator always sets `Cache-Control: max-age=...`
    and an `ETag` on responses it wraps, which makes browsers cache GET
    responses client-side. That's independent from (and bypasses) our
    server-side Redis cache invalidation via `clear_cache`, so mutations
    would appear to have no effect until the browser cache expired. We only
    want the Redis-layer cache, so strip any such headers here.
    """
    response: Response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    if "ETag" in response.headers:
        del response.headers["ETag"]
    return response


app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(cities.router)
app.include_router(countries.router)
app.include_router(days.router)
app.include_router(email.router)
app.include_router(insights.router)
app.include_router(months.router)
app.include_router(storage.router)
app.include_router(workspaces.router)
app.include_router(trackables.router)
app.include_router(trackable_types.router)
app.include_router(suggestions.router)
app.include_router(tags.router)

register_exception_handlers(app)


@app.get("/", response_model=Msg[None])
async def start() -> Msg[None]:
    return Msg(code=200, msg="Memoryful is running!")
