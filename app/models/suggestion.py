import datetime as dt
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import IDMixin


class Suggestion(Base, IDMixin):
    __tablename__ = "suggestions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    model_id: Mapped[UUID] = mapped_column(ForeignKey("chat_models.id"))
    content: Mapped[str]
    date: Mapped[dt.date]

    user: Mapped["User"] = relationship(back_populates="suggestions")
    chat_model: Mapped["ChatModel"] = relationship(back_populates="suggestions")

from .user import User
from .chat_model import ChatModel