import datetime as dt
from uuid import UUID

from sqlalchemy import ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import IDMixin, TimestampMixin
from app.models.custom_types import PydanticType
from app.schemas.font_awesome import FAIcon


class Insight(Base, IDMixin, TimestampMixin):
    __tablename__ = "insights"

    user_id: Mapped[UUID] = mapped_column()
    model_id: Mapped[UUID] = mapped_column(ForeignKey("chat_models.id"))
    insight_type_id: Mapped[UUID] = mapped_column(ForeignKey("insight_types.id"))
    timestamp: Mapped[int] = mapped_column()

    date_begin: Mapped[dt.date]  # Insight duration begins at this date
    description: Mapped[str]
    icon: Mapped[FAIcon | None] = mapped_column(PydanticType(FAIcon), default=None)
    content: Mapped[str]

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

    user: Mapped["User"] = relationship(back_populates="insights")
    chat_model: Mapped["ChatModel"] = relationship(back_populates="insights")
    insight_type: Mapped["InsightType"] = relationship(back_populates="insights")
    day: Mapped["Day"] = relationship(
        back_populates="insights",
        overlaps="user,insights"
    )

from .chat_model import ChatModel
from .day import Day
from .insight_type import InsightType
from .user import User
