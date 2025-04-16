from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import IDMixin


class LearningItem(Base, IDMixin):
    __tablename__ = "learning_items"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str]
    description: Mapped[str | None]
    icon: Mapped[str | None]

    user: Mapped["User"] = relationship(back_populates="learning_items")
    learning_progresses: Mapped[list["LearningProgress"]] = relationship(back_populates="learning_item")

from .user import User
from .learning_progress import LearningProgress