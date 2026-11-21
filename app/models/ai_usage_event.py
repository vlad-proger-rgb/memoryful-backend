from decimal import Decimal
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.enums import AiUsagePurpose
from app.models._mixins import IDMixin, TimestampMixin


class AiUsageEvent(Base, IDMixin, TimestampMixin):
    """One provider call. The cost is fixed at write time, so later price changes leave it."""

    __tablename__ = "ai_usage_events"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    chat_model_id: Mapped[UUID] = mapped_column(ForeignKey("chat_models.id"))
    purpose: Mapped[AiUsagePurpose] = mapped_column(
        Enum(AiUsagePurpose, native_enum=False, length=32)
    )
    input_tokens: Mapped[int]
    cached_input_tokens: Mapped[int]
    output_tokens: Mapped[int]
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(18, 12))

    __table_args__ = (Index("ix_ai_usage_events_user_id_created_at", "user_id", "created_at"),)
