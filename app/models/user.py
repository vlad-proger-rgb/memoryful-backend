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
    is_enabled: Mapped[bool] = mapped_column(default=True)
    first_name: Mapped[str | None]
    last_name: Mapped[str | None]
    age: Mapped[int | None]
    bio: Mapped[str | None]
    job_title: Mapped[str | None]
    photo: Mapped[str | None]

    country: Mapped["Country"] = relationship(back_populates="users")
    city: Mapped["City"] = relationship(back_populates="users")
    tokens: Mapped["UserToken"] = relationship(back_populates="user")
    months: Mapped[list["Month"]] = relationship(back_populates="user")
    days: Mapped[list["Day"]] = relationship(back_populates="user")
    tags: Mapped[list["Tag"]] = relationship(back_populates="user")
    learning_items: Mapped[list["LearningItem"]] = relationship(back_populates="user")
    search_history: Mapped[list["SearchHistory"]] = relationship(back_populates="user")
    chats: Mapped[list["Chat"]] = relationship(back_populates="user")
    insights: Mapped[list["Insight"]] = relationship(back_populates="user")
    suggestions: Mapped[list["Suggestion"]] = relationship(back_populates="user")
    learning_progresses: Mapped[list["LearningProgress"]] = relationship(
        back_populates="user", overlaps="learning_progresses",
    )


from .user_token import UserToken
from .month import Month
from .day import Day
from .tag import Tag
from .learning_item import LearningItem
from .learning_progress import LearningProgress
from .search_history import SearchHistory
from .chat import Chat
from .insight import Insight
from .suggestion import Suggestion
from .country import Country
from .city import City
