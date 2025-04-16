from uuid import UUID

from sqlalchemy import ForeignKey, ARRAY, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import TimestampWithUpdateMixin


class Day(Base, TimestampWithUpdateMixin):
    __tablename__ = "days"

    timestamp: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    city_id: Mapped[UUID] = mapped_column(ForeignKey("cities.id"))
    description: Mapped[str]
    content: Mapped[str]
    steps: Mapped[int | None]
    starred: Mapped[bool] = mapped_column(default=False)
    main_image: Mapped[str]
    images: Mapped[list[str]] = mapped_column(ARRAY(String))

    user: Mapped["User"] = relationship(back_populates="days")
    city: Mapped["City"] = relationship(back_populates="days")
    learning_progresses: Mapped[list["LearningProgress"]] = relationship(
        back_populates="day", overlaps="learning_progresses",
    )

from .user import User
from .city import City
from .learning_progress import LearningProgress