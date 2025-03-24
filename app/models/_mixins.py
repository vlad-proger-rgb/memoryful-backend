import uuid
import datetime as dt
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class IDMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, unique=True, default=uuid.uuid4)

class TimestampMixin:
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now()
    )

class TimestampWithUpdateMixin(TimestampMixin):
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(), 
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(default=False)

class ActiveStatusMixin:
    is_active: Mapped[bool] = mapped_column(default=True)
