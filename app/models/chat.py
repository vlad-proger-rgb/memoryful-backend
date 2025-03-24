from uuid import UUID

from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import IDMixin, TimestampWithUpdateMixin, SoftDeleteMixin


class Chat(Base, IDMixin, TimestampWithUpdateMixin, SoftDeleteMixin):
    __tablename__ = "chats"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    model_id: Mapped[UUID] = mapped_column(ForeignKey("chat_models.id"))
    title: Mapped[str]
    messages: Mapped[list[dict[str, str]]] = mapped_column(JSON)

    user: Mapped["User"] = relationship(back_populates="chats")
    chat_model: Mapped["ChatModel"] = relationship(back_populates="chats")

from .user import User
from .chat_model import ChatModel