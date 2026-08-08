from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
)
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import CACHE_TTL_DAYS
from app.core.cache import cached, clear_cache
from app.core.database import get_db
from app.core.deps import StorageServiceDep, get_current_user
from app.core.storage.service import StorageService
from app.core.storage.utils import is_video_key, orphaned_keys
from app.enums import CacheNamespace
from app.models import Month
from app.schemas import (
    MonthBase,
    MonthInDB as M,
    Msg,
    ResolvedBackground,
)

router = APIRouter(
    prefix="/months",
    tags=["Months"],
)


async def _with_resolved(
    storage: StorageService,
    user_id: UUID,
    month: Month,
) -> M:
    model = M.model_validate(month)

    if month.background_image:
        model.resolved = ResolvedBackground(
            key=month.background_image,
            url=await storage.resolve_url(user_id, month.background_image),
            is_video=is_video_key(month.background_image),
            placeholder=month.background_placeholder,
        )

    return model


@router.get("/{year}", response_model=Msg[list[M]])
@cached(expire=CACHE_TTL_DAYS, namespace=CacheNamespace.months)
async def get_months(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    year: int,
    storage_service: StorageServiceDep,
) -> Msg[list[M]]:
    stmt = select(Month).where(Month.user_id == user_id, Month.year == year)
    months_result = await db.execute(stmt)
    months = months_result.scalars()

    data = [await _with_resolved(storage_service, user_id, month) for month in months]
    return Msg(code=200, msg="Months retrieved", data=data)


@router.get("/{year}/{month_number}", response_model=Msg[M])
@cached(expire=CACHE_TTL_DAYS, namespace=CacheNamespace.months)
async def get_month(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    year: int,
    month_number: int,
    storage_service: StorageServiceDep,
) -> Msg[M]:
    stmt = select(Month).where(
        Month.user_id == user_id,
        Month.year == year,
        Month.month == month_number,
    )
    result = await db.scalars(stmt)
    month = result.first()
    if not month:
        raise HTTPException(404, "Month not found")

    return Msg(
        code=200,
        msg="Month retrieved",
        data=await _with_resolved(storage_service, user_id, month),
    )


@router.post("/", response_model=Msg[None])
async def create_month(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    data: MonthBase,
) -> Msg[None]:
    db.add(
        Month(
            year=data.year,
            month=data.month,
            user_id=user_id,
            description=data.description,
            background_image=data.background_image,
            background_placeholder=data.background_placeholder,
            top_day_timestamp=data.top_day_timestamp,
        )
    )
    await db.commit()

    await clear_cache(CacheNamespace.months, user_id)
    return Msg(code=200, msg="Month created")


@router.put("/", response_model=Msg[None])
async def update_month(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    data: MonthBase,
    storage_service: StorageServiceDep,
    background_tasks: BackgroundTasks,
) -> Msg[None]:
    payload = data.model_dump(exclude_unset=True)

    previous_image = await db.scalar(
        select(Month.background_image).where(
            Month.user_id == user_id, Month.year == data.year, Month.month == data.month
        )
    )
    # An unsent field keeps its current value, so it must not count as orphaned.
    orphaned = orphaned_keys(previous_image, payload.get("background_image", previous_image))

    stmt = (
        update(Month)
        .where(Month.user_id == user_id, Month.year == data.year, Month.month == data.month)
        .values(**payload)
    )  # fmt: skip
    await db.execute(stmt)
    await db.commit()
    await clear_cache(CacheNamespace.months, user_id)
    background_tasks.add_task(storage_service.delete_objects, user_id, orphaned)
    return Msg(code=200, msg="Month updated")
