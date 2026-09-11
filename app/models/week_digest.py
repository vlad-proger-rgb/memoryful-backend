import datetime as dt
from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import IDMixin, TimestampWithUpdateMixin


class WeekDigest(Base, IDMixin, TimestampWithUpdateMixin):
    """One AI pass over a finished week."""

    __tablename__ = "week_digests"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    model_id: Mapped[UUID] = mapped_column(ForeignKey("chat_models.id"))

    week_start: Mapped[dt.date]  # Monday, UTC; the Sunday is always six days later

    title: Mapped[str]
    summary: Mapped[str]
    #: [{"description": str, "icon": {...} | None, "content": str}]
    sections: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list)

    source_day_count: Mapped[int]

    __table_args__ = (UniqueConstraint("user_id", "week_start"),)

    user: Mapped["User"] = relationship(back_populates="week_digests")
    chat_model: Mapped["ChatModel"] = relationship(back_populates="week_digests")


from .chat_model import ChatModel
from .user import User
