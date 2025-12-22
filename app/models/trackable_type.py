from uuid import UUID

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.custom_types import PydanticType
from app.models._mixins import IDMixin
from app.schemas.font_awesome import FAIcon


class TrackableType(Base, IDMixin):
    __tablename__ = "trackable_types"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    description: Mapped[str | None]
    value_type: Mapped[str]
    icon: Mapped[FAIcon | None] = mapped_column(PydanticType(FAIcon), default=None)
    meta_schema: Mapped[dict | None] = mapped_column(JSON, default=None)

    user: Mapped["User"] = relationship(back_populates="trackable_types")
    trackable_items: Mapped[list["TrackableItem"]] = relationship(back_populates="type")

from .trackable_item import TrackableItem
from .user import User
