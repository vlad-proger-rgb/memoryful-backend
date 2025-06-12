from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
)
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Month
from app.core.deps import get_current_user
from app.schemas import (
    Msg,
    MonthInDB as M,
    MonthBase,
)


router = APIRouter(
    prefix="/months",
    tags=["Months"],
)


@router.get("/{year}", response_model=Msg[list[M]])
async def get_months(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    year: int,
) -> Msg[list[M]]:
    stmt = select(Month).where(Month.user_id == user_id, Month.year == year)
    months_result = await db.execute(stmt)
    months = months_result.scalars()

    return Msg(code=200, msg="Months retrieved", data=[M.model_validate(month) for month in months])


@router.get("/{year}/{month_number}", response_model=Msg[M])
async def get_month(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    year: int,
    month_number: int,
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

    return Msg(code=200, msg="Month retrieved", data=M.model_validate(month))


@router.post("/", response_model=Msg[None])
async def create_month(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    data: MonthBase,
) -> Msg[None]:
    db.add(Month(
        year=data.year,
        month=data.month,
        user_id=user_id,
        description=data.description,
        background_image=data.background_image,
        top_day_timestamp=data.top_day_timestamp,
    ))
    await db.commit()

    return Msg(code=200, msg="Month created")


@router.put("/", response_model=Msg[None])
async def update_month(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    data: MonthBase,
) -> Msg[None]:
    stmt = (
        update(Month)
        .where(Month.user_id == user_id, Month.year == data.year, Month.month == data.month)
        .values(**data.model_dump(exclude_unset=True))
    )
    await db.execute(stmt)
    await db.commit()
    return Msg(code=200, msg="Month updated")

