from uuid import UUID

from sqlalchemy import ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import IDMixin


class TrackableProgress(Base, IDMixin):
    __tablename__ = "trackable_progress"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    trackable_item_id: Mapped[UUID] = mapped_column(ForeignKey("trackable_items.id"))
    timestamp: Mapped[int] = mapped_column()
    value: Mapped[float]
    description: Mapped[str | None]

    user: Mapped["User"] = relationship(
        back_populates="trackable_progresses",
        overlaps="day,trackable_progresses",
    )
    trackable_item: Mapped["TrackableItem"] = relationship(back_populates="progresses")
    day: Mapped["Day"] = relationship(
        back_populates="trackable_progresses",
        foreign_keys=[timestamp, user_id],
        overlaps="user,trackable_progresses",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["timestamp", "user_id"], 
            ["days.timestamp", "days.user_id"],
        ),
    )


from .user import User
from .day import Day
from .trackable_item import TrackableItem
