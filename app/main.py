from typing import AsyncIterator, Callable
import asyncio
import logging
import sys

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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set specific logger for AI operations to be more verbose
ai_logger = logging.getLogger('app.ai')
ai_logger.setLevel(logging.DEBUG)

from app.init_db import init_db
from app.schemas import Msg
from app.core.exceptions import register_exception_handlers
from app.core.database import Base, AsyncSessionLocal, engine
from app.core.config import cache_redis
from app.core.cache import CACHE_PREFIX
from app.core.settings import (
    ALLOWED_ORIGINS,
    ALLOW_CREDENTIALS,
    ALLOWED_HEADERS,
    ALLOWED_METHODS,
    ENVIRONMENT,
    SEED_DB_ON_EMPTY,
)
from app.models import User

from app.routers import (
    auth,
    chat_models,
    chats,
    cities,
    countries,
    days,
    email,
    insights,
    months,
    storage,
    suggestions,
    tags,
    trackables,
    trackable_types,
    workspaces,
)



async def run_migrations() -> None:
    from alembic.config import Config
    from alembic import command

    def _upgrade() -> None:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _upgrade)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    FastAPICache.init(RedisBackend(cache_redis), prefix=CACHE_PREFIX)
    # await run_migrations()
    async with AsyncSessionLocal() as session:
        if ENVIRONMENT == "development" and SEED_DB_ON_EMPTY:
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
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
)


@app.middleware("http")
async def disable_http_caching(request: Request, call_next: Callable):
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


app.include_router(auth.router)
app.include_router(chat_models.router)
app.include_router(chats.router)
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
