from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.settings import get_settings

settings = get_settings()


def get_engine() -> AsyncEngine:
    """Create database engine with Cloud SQL support for production"""

    # Previously we used Cloud SQL (Cloud Run), now we switched to Neon.
    # Kept for reference / in case Cloud SQL is used again in the future.
    if settings.environment == "production" and settings.postgres_host.startswith("/cloudsql/"):
        from google.cloud.sql.connector import Connector

        async def getconn() -> Any:
            connector = Connector()
            conn = await connector.connect_async(
                settings.postgres_host.replace("/cloudsql/", ""),
                "asyncpg",
                user=settings.postgres_user,
                password=settings.postgres_password,
                db=settings.postgres_db,
            )
            return conn

        return create_async_engine(
            "postgresql+asyncpg://",
            async_creator=getconn,
            echo=settings.sql_echo,
            future=True,
        )
    else:
        # Standard asyncpg connection (used for Neon in production, and for local/dev Postgres)
        return create_async_engine(
            settings.main_database_url,
            echo=settings.sql_echo,
            future=True,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={
                "ssl": settings.postgres_sslmode,
                "server_settings": {"application_name": "memoryful-backend"},
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
