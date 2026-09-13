from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AiModelPreference(Base):
    __tablename__ = "ai_model_preferences"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    purpose: Mapped[str] = mapped_column(primary_key=True)
    model_id: Mapped[UUID] = mapped_column(ForeignKey("chat_models.id"))

    user: Mapped["User"] = relationship(back_populates="ai_model_preferences")
    chat_model: Mapped["ChatModel"] = relationship(back_populates="ai_model_preferences")


from .chat_model import ChatModel
from .user import User
