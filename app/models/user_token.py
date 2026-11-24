import datetime as dt
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import IDMixin, TimestampMixin


class UserToken(Base, IDMixin, TimestampMixin):
    """One signed-in session; its id is the `sid` claim of every token it issues."""

    __tablename__ = "user_tokens"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    refresh_token_hash: Mapped[str] = mapped_column(index=True)
    previous_refresh_token_hash: Mapped[str | None] = mapped_column(nullable=True, default=None)
    rotated_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    expires_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.UTC) + dt.timedelta(days=7),
    )

    user: Mapped["User"] = relationship(back_populates="tokens")


from .user import User
