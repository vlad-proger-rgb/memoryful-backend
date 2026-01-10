from uuid import UUID
import datetime as dt

from sqlalchemy import ForeignKey, ARRAY, String, Table, Column, Integer, ForeignKeyConstraint, DateTime
from sqlalchemy.dialects.postgresql import UUID as SQLAlchemyUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import TimestampWithUpdateMixin


days_tags = Table(
    "days_tags",
    Base.metadata,
    Column("day_timestamp", Integer, primary_key=True),
    Column("user_id", SQLAlchemyUUID(as_uuid=True), primary_key=True),
    Column("tag_id", SQLAlchemyUUID(as_uuid=True), primary_key=True),
    ForeignKeyConstraint(
        ['day_timestamp', 'user_id'],
        ['days.timestamp', 'days.user_id']
    ),
    ForeignKeyConstraint(
        ['tag_id'],
        ['tags.id']
    )
)


class Day(Base, TimestampWithUpdateMixin):
    __tablename__ = "days"

    timestamp: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    city_id: Mapped[UUID] = mapped_column(ForeignKey("cities.id"))
    description: Mapped[str | None]
    content: Mapped[str]
    steps: Mapped[int | None]
    starred: Mapped[bool] = mapped_column(default=False)
    main_image: Mapped[str | None]
    images: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_generated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="days")
    city: Mapped["City"] = relationship(back_populates="days")
    tags: Mapped[list["Tag"]] = relationship(
        secondary=days_tags,
        primaryjoin="and_(Day.timestamp==days_tags.c.day_timestamp, Day.user_id==days_tags.c.user_id)",
        secondaryjoin="Tag.id==days_tags.c.tag_id",
        back_populates="days"
    )
    trackable_progresses: Mapped[list["TrackableProgress"]] = relationship(
        back_populates="day", 
        overlaps="user,trackable_progresses"
    )

from .user import User
from .city import City
from .trackable_progress import TrackableProgress
from .tag import Tag
