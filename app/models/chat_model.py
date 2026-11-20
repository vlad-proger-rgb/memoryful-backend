from decimal import Decimal

from sqlalchemy import Numeric, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import ActiveStatusMixin, IDMixin


class ChatModel(Base, IDMixin, ActiveStatusMixin):
    __tablename__ = "chat_models"

    slug: Mapped[str | None] = mapped_column(unique=True, default=None)
    label: Mapped[str]
    name: Mapped[str]
    provider: Mapped[str] = mapped_column(default="other")
    gateway: Mapped[str | None] = mapped_column(default=None)
    no_sampling: Mapped[bool] = mapped_column(default=False, server_default=false())
    is_default: Mapped[bool] = mapped_column(default=False)
    sort_order: Mapped[int] = mapped_column(default=0)
    input_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), default=None)
    cached_input_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), default=None)
    output_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), default=None)
    context_limit: Mapped[int | None] = mapped_column(default=None)
    output_limit: Mapped[int | None] = mapped_column(default=None)

    chats: Mapped[list["Chat"]] = relationship(back_populates="chat_model")
    insights: Mapped[list["Insight"]] = relationship(back_populates="chat_model")
    week_digests: Mapped[list["WeekDigest"]] = relationship(back_populates="chat_model")
    ai_model_preferences: Mapped[list["AiModelPreference"]] = relationship(
        back_populates="chat_model"
    )


from .ai_model_preference import AiModelPreference
from .chat import Chat
from .insight import Insight
from .week_digest import WeekDigest
