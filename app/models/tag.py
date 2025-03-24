from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import IDMixin


class Tag(Base, IDMixin):
    __tablename__ = "tags"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    icon: Mapped[str | None] = mapped_column(default=None)
    color: Mapped[str | None] = mapped_column(default=None)  # ?

    user: Mapped["User"] = relationship(back_populates="tags")

from .user import User