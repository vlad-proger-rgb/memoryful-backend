from typing import AsyncIterator
import sys

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.append("..")

from app.init_db import init_db
from app.schemas import Msg
from app.core.exceptions import register_exception_handlers
from app.core.database import Base, AsyncSessionLocal, engine
from app.core.settings import (
    ALLOWED_ORIGINS,
    ALLOW_CREDENTIALS,
    ALLOWED_HEADERS,
    ALLOWED_METHODS,
)

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
    suggestions,
    tags,
    trackables,
    trackable_types,
)



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
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


app.include_router(auth.router)
app.include_router(chat_models.router)
app.include_router(chats.router)
app.include_router(cities.router)
app.include_router(countries.router)
app.include_router(days.router)
app.include_router(email.router)
app.include_router(insights.router)
app.include_router(months.router)
app.include_router(trackables.router)
app.include_router(trackable_types.router)
app.include_router(suggestions.router)
app.include_router(tags.router)

register_exception_handlers(app)


@app.get("/", response_model=Msg[None])
async def start() -> Msg[None]:
    return Msg(code=200, msg="Memoryful is running!")
