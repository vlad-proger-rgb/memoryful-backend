from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Month(Base):
    __tablename__ = "months"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str | None]
    background_image: Mapped[str | None]
    top_day_timestamp: Mapped[int | None]

    user: Mapped["User"] = relationship(back_populates="months")

from .user import User