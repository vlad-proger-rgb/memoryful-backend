from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import IDMixin
from app.models.custom_types import PydanticType
from app.schemas.font_awesome import FAIcon
from .day import days_tags


class Tag(Base, IDMixin):
    __tablename__ = "tags"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    icon: Mapped[FAIcon | None] = mapped_column(PydanticType(FAIcon), default=None)
    color: Mapped[str | None] = mapped_column(default=None)  # ?

    user: Mapped["User"] = relationship(back_populates="tags")
    days: Mapped[list["Day"]] = relationship(
        secondary=days_tags,
        primaryjoin="Tag.id==days_tags.c.tag_id",
        secondaryjoin="and_(Day.timestamp==days_tags.c.day_timestamp, Day.user_id==days_tags.c.user_id)",
        back_populates="tags"
    )

from .user import User
from .day import Day
