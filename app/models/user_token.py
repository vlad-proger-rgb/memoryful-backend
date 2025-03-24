import datetime as dt
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import Base
from app.models._mixins import IDMixin, TimestampMixin


class UserToken(Base, IDMixin, TimestampMixin):
    __tablename__ = "user_tokens"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    refresh_token_hash: Mapped[str]
    expires_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.UTC) + dt.timedelta(days=7),
    )

    user: Mapped["User"] = relationship(back_populates="tokens")

    @classmethod
    async def find_by_refresh_token(cls, db: AsyncSession, token: str) -> "UserToken | None":
        from app.core.security import hash_refresh_token

        refresh_token_hash = hash_refresh_token(token)
        stmt = select(cls).where(cls.refresh_token_hash == refresh_token_hash)
        token_db: UserToken | None = (await db.scalars(stmt)).one_or_none()

        if not token_db:
            return None

        if token_db.expires_at < dt.datetime.now(dt.UTC):
            await db.delete(token_db)
            await db.commit()
            return None

        return token_db

from .user import User