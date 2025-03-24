from uuid import UUID

from sqlalchemy import ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import IDMixin


class LearningProgress(Base, IDMixin):
    __tablename__ = "learning_progress"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    learning_item_id: Mapped[UUID] = mapped_column(ForeignKey("learning_items.id"))
    timestamp: Mapped[int] = mapped_column()
    time_involved: Mapped[int]  # in minutes

    user: Mapped["User"] = relationship(back_populates="learning_progresses")
    learning_item: Mapped["LearningItem"] = relationship(back_populates="learning_progresses")
    day: Mapped["Day"] = relationship(
        back_populates="learning_progresses",
        foreign_keys=[timestamp, user_id],
    )

    __table_args__ = (
        ForeignKeyConstraint(["timestamp", "user_id"], ["days.timestamp", "days.user_id"]),
    )


from .user import User
from .day import Day
from .learning_item import LearningItem