from sqlalchemy.orm import Mapped, relationship
from app.core.database import Base
from app.models._mixins import IDMixin


class ChatModel(Base, IDMixin):
    __tablename__ = "chat_models"

    label: Mapped[str]
    name: Mapped[str]

    chats: Mapped[list["Chat"]] = relationship(back_populates="chat_model")
    suggestions: Mapped[list["Suggestion"]] = relationship(back_populates="chat_model")
    insights: Mapped[list["Insight"]] = relationship(back_populates="chat_model")

from .chat import Chat
from .suggestion import Suggestion
from .insight import Insight
