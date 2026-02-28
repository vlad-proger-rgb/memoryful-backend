from typing import AsyncGenerator

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from app.core.settings import MAIN_DATABASE_URL, POSTGRES_SSLMODE


engine: AsyncEngine = create_async_engine(
    MAIN_DATABASE_URL,
    echo=True,
    future=True,
    connect_args={
        "ssl": POSTGRES_SSLMODE,
        "server_settings": {
            "application_name": "memoryful-backend"
        },
    },
)

class Base(DeclarativeBase):
    pass

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator:
    async with AsyncSessionLocal() as db:
        yield db
