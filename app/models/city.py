from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import IDMixin


class City(Base, IDMixin):
    __tablename__ = "cities"

    name: Mapped[str]
    country_id: Mapped[UUID] = mapped_column(ForeignKey("countries.id"))

    country: Mapped["Country"] = relationship(back_populates="cities")
    days: Mapped[list["Day"]] = relationship(back_populates="city")
    users: Mapped[list["User"]] = relationship(back_populates="city")

from .country import Country
from .day import Day
from .user import User
