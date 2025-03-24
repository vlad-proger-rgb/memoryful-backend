from uuid import UUID

from sqlalchemy import ForeignKey, ARRAY, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import IDMixin, TimestampMixin


class SearchHistory(Base, IDMixin, TimestampMixin):
    __tablename__ = "search_history"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    query: Mapped[str]
    results: Mapped[list[str]] = mapped_column(ARRAY(String))

    user: Mapped["User"] = relationship(back_populates="search_history")

from .user import User