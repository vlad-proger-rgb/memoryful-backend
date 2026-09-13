from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import IDMixin, TimestampWithUpdateMixin


class User(Base, IDMixin, TimestampWithUpdateMixin):
    __tablename__ = "users"

    country_id: Mapped[UUID | None] = mapped_column(ForeignKey("countries.id"))
    city_id: Mapped[UUID | None] = mapped_column(ForeignKey("cities.id"))
    email: Mapped[str] = mapped_column(unique=True)
    google_sub: Mapped[str | None] = mapped_column(unique=True, default=None)
    is_enabled: Mapped[bool] = mapped_column(default=True)
    first_name: Mapped[str | None]
    last_name: Mapped[str | None]
    age: Mapped[int | None]
    bio: Mapped[str | None]
    photo: Mapped[str | None]

    country: Mapped["Country"] = relationship(back_populates="users")
    city: Mapped["City"] = relationship(back_populates="users")
    tokens: Mapped["UserToken"] = relationship(back_populates="user")
    months: Mapped[list["Month"]] = relationship(back_populates="user")
    days: Mapped[list["Day"]] = relationship(back_populates="user")
    tags: Mapped[list["Tag"]] = relationship(back_populates="user")
    search_history: Mapped[list["SearchHistory"]] = relationship(back_populates="user")
    chats: Mapped[list["Chat"]] = relationship(back_populates="user")
    insights: Mapped[list["Insight"]] = relationship(back_populates="user")
    trackable_types: Mapped[list["TrackableType"]] = relationship(back_populates="user")
    trackable_items: Mapped[list["TrackableItem"]] = relationship(back_populates="user")
    trackable_progresses: Mapped[list["TrackableProgress"]] = relationship(
        back_populates="user", overlaps="day,trackable_progresses"
    )

    week_digests: Mapped[list["WeekDigest"]] = relationship(back_populates="user")
    workspace_backgrounds: Mapped[list["WorkspaceBackground"]] = relationship(back_populates="user")
    ai_model_preferences: Mapped[list["AiModelPreference"]] = relationship(back_populates="user")


from .ai_model_preference import AiModelPreference
from .chat import Chat
from .city import City
from .country import Country
from .day import Day
from .insight import Insight
from .month import Month
from .search_history import SearchHistory
from .tag import Tag
from .trackable_item import TrackableItem
from .trackable_progress import TrackableProgress
from .trackable_type import TrackableType
from .user_token import UserToken
from .week_digest import WeekDigest
from .workspace import WorkspaceBackground
