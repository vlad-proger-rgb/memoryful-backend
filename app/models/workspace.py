from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)

    dashboard_background: Mapped[str | None]
    day_background: Mapped[str | None]
    search_background: Mapped[str | None]
    settings_background: Mapped[str | None]

    user: Mapped["User"] = relationship(back_populates="workspace")


from .user import User
