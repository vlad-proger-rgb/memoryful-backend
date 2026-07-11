from typing import AsyncGenerator

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

    # Previously we used Cloud SQL (Cloud Run), now we switched to Neon.
    # Kept for reference / in case Cloud SQL is used again in the future.
    if ENVIRONMENT == "production" and POSTGRES_HOST.startswith("/cloudsql/"):
        from google.cloud.sql.connector import Connector

        async def getconn():
            connector = Connector()
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
        # Standard asyncpg connection (used for Neon in production, and for local/dev Postgres)
        return create_async_engine(
            MAIN_DATABASE_URL,
            echo=True,
            future=True,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={
                "ssl": POSTGRES_SSLMODE,
                "server_settings": {
                    "application_name": "memoryful-backend"
                },
                # Required for Neon's pooled (-pooler) endpoint: PgBouncer's
                # transaction pooling mode is incompatible with asyncpg's
                # server-side prepared statement cache.
                "statement_cache_size": 0,
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
