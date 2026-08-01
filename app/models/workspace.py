from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WorkspaceBackground(Base):
    """One row per page the user has customized. No row means the default."""

    __tablename__ = "workspace_backgrounds"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    # Plain text rather than a DB enum, so adding a page needs no migration.
    # `WorkspacePage` validates it at the API boundary.
    page: Mapped[str] = mapped_column(primary_key=True)
    object_key: Mapped[str]
    placeholder: Mapped[str | None]

    user: Mapped["User"] = relationship(back_populates="workspace_backgrounds")


from .user import User
