from uuid import UUID

from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import IDMixin
from app.models.custom_types import PydanticType
from app.schemas.font_awesome import FAIcon


class TrackableItem(Base, IDMixin):
    __tablename__ = "trackable_items"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    type_id: Mapped[UUID] = mapped_column(ForeignKey("trackable_types.id"))
    title: Mapped[str]
    description: Mapped[str | None]
    icon: Mapped["FAIcon | None"] = mapped_column(PydanticType(FAIcon), default=None)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

    user: Mapped["User"] = relationship(back_populates="trackable_items")
    type: Mapped["TrackableType"] = relationship(back_populates="trackable_items")
    progresses: Mapped[list["TrackableProgress"]] = relationship(back_populates="trackable_item")


from .user import User
from .trackable_type import TrackableType
from .trackable_progress import TrackableProgress
