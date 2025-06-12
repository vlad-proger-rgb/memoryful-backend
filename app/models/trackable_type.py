from app.core.database import Base
from app.models._mixins import IDMixin
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship


class TrackableType(Base, IDMixin):
    __tablename__ = "trackable_types"

    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None]
    value_type: Mapped[str]
    icon: Mapped[str | None]
    meta_schema: Mapped[dict | None] = mapped_column(JSON, default=None)

    trackable_items: Mapped[list["TrackableItem"]] = relationship(back_populates="type")

from .trackable_item import TrackableItem
