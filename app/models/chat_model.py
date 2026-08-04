from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import ActiveStatusMixin, IDMixin


class ChatModel(Base, IDMixin, ActiveStatusMixin):
    __tablename__ = "chat_models"

    label: Mapped[str]  # human-facing name shown in the selector
    name: Mapped[str]  # exact model id passed to the provider SDK (e.g. "gemini-2.5-flash-lite")
    provider: Mapped[str] = mapped_column(
        default="other"
    )  # app.enums.provider.Provider value; drives routing
    region: Mapped[str | None] = mapped_column(
        default=None
    )  # Vertex location override; None -> VERTEX_LOCATION
    supports_tools: Mapped[bool] = mapped_column(default=True)  # can this model do MCP/tool calling
    is_default: Mapped[bool] = mapped_column(default=False)  # fallback pick for background jobs
    sort_order: Mapped[int] = mapped_column(default=0)  # ascending display order in the selector

    chats: Mapped[list["Chat"]] = relationship(back_populates="chat_model")
    suggestions: Mapped[list["Suggestion"]] = relationship(back_populates="chat_model")
    insights: Mapped[list["Insight"]] = relationship(back_populates="chat_model")


from .chat import Chat
from .insight import Insight
from .suggestion import Suggestion
