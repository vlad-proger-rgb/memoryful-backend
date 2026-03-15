from typing import AsyncGenerator
import asyncio

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from app.core.settings import (
    MAIN_DATABASE_URL, 
    POSTGRES_SSLMODE,
    POSTGRES_HOST,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    POSTGRES_DB,
    ENVIRONMENT
)


def get_engine() -> AsyncEngine:
    """Create database engine with Cloud SQL support for production"""

    # Check if running on Cloud Run with Cloud SQL
    if ENVIRONMENT == "production" and POSTGRES_HOST.startswith("/cloudsql/"):
        from google.cloud.sql.connector import Connector

        loop = asyncio.get_event_loop()
        connector = Connector(loop=loop)

        async def getconn():
            conn = await connector.connect_async(
                POSTGRES_HOST.replace("/cloudsql/", ""),
                "asyncpg",
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                db=POSTGRES_DB,
            )
            return conn

        return create_async_engine(
            "postgresql+asyncpg://",
            async_creator=getconn,
            echo=True,
            future=True,
        )
    else:
        # Standard connection for development
        return create_async_engine(
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


engine: AsyncEngine = get_engine()

class Base(DeclarativeBase):
    pass

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator:
    async with AsyncSessionLocal() as db:
        yield db
