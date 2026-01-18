import datetime as dt
from uuid import UUID

from sqlalchemy import ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import IDMixin
from app.models.custom_types import PydanticType
from app.schemas.font_awesome import FAIcon


class Suggestion(Base, IDMixin):
    __tablename__ = "suggestions"

    user_id: Mapped[UUID] = mapped_column()
    model_id: Mapped[UUID] = mapped_column(ForeignKey("chat_models.id"))
    timestamp: Mapped[int] = mapped_column()

    description: Mapped[str]
    icon: Mapped[FAIcon | None] = mapped_column(PydanticType(FAIcon), default=None)
    content: Mapped[str]
    date: Mapped[dt.date]

    __table_args__ = (
        ForeignKeyConstraint(
            ['user_id'],
            ['users.id']
        ),
        ForeignKeyConstraint(
            ['timestamp', 'user_id'],
            ['days.timestamp', 'days.user_id']
        ),
    )

    user: Mapped["User"] = relationship(back_populates="suggestions")
    chat_model: Mapped["ChatModel"] = relationship(back_populates="suggestions")
    day: Mapped["Day"] = relationship(
        back_populates="suggestions",
        overlaps="user,suggestions"
    )

from .day import Day
from .chat_model import ChatModel
from .user import User
