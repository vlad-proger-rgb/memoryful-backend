import datetime as dt

from sqlalchemy import Interval
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._mixins import IDMixin


class InsightType(Base, IDMixin):
    __tablename__ = "insight_types"

    name: Mapped[str]
    duration: Mapped[dt.timedelta] = mapped_column(Interval)

    insights: Mapped[list["Insight"]] = relationship(back_populates="insight_type")

from .insight import Insight
