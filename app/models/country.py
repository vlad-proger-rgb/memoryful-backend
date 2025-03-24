from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models._mixins import IDMixin


class Country(Base, IDMixin):
    __tablename__ = "countries"

    name: Mapped[str] = mapped_column(unique=True)
    code: Mapped[str] = mapped_column(unique=True)

    cities: Mapped[list["City"]] = relationship(back_populates="country")

from .city import City
