import json
from typing import Annotated, Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Query,
)
from sqlalchemy import select, update, delete, exists, func
from sqlalchemy.orm import selectinload, load_only
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Day, City, LearningItem, LearningProgress
from app.core.deps import get_current_user
from app.schemas import (
    Msg,
    DayListItem,
    DayDetail,
    DayCreate,
    DayUpdate,
)


router = APIRouter(
    prefix="/days",
    tags=["Days"],
)


@router.get("/")
async def get_days(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str | None = Query(None),
    view: Literal["list", "detail"] = Query("list", description="View type to return"),
    filters: str | None = Query(None),
) -> Msg[list[DayListItem | DayDetail]]:
    stmt = select(Day).where(Day.user_id == user_id)

    if filters:
        try:
            filters_dict: dict = json.loads(filters)
            for key, value in filters_dict.items():
                if hasattr(Day, key):
                    stmt = stmt.where(getattr(Day, key) == value)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid JSON format for filters")

    if sort_by:
        for sort_item in sort_by.split(","):
            field, order = sort_item.split(":")
            if hasattr(Day, field):
                order_by_column = getattr(Day, field)
                stmt = stmt.order_by(order_by_column.asc() if order == "asc" else order_by_column.desc())

    if view == "list":
        stmt = stmt.options(
            load_only(
                Day.timestamp,
                Day.description,
                Day.steps,
                Day.starred,
                Day.main_image,
            ),
            selectinload(Day.city),
            selectinload(Day.learning_progresses).selectinload(LearningProgress.learning_item),
        )
    else:
        stmt = stmt.options(
            selectinload(Day.learning_progresses),
            selectinload(Day.city),
        )

    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    days = list(result.scalars().unique())

    response_model = DayDetail if view == "detail" else DayListItem
    return Msg(
        code=200,
        msg="Days retrieved",
        data=[response_model.model_validate(day) for day in days]
    )


@router.get("/random", response_model=Msg[DayDetail])
async def get_random_day(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    timestamp_start: int | None = Query(None, alias="timestampStart"),
    timestamp_end: int | None = Query(None, alias="timestampEnd"),
) -> Msg[DayDetail]:
    print(f"timestamp_start: {timestamp_start}, timestamp_end: {timestamp_end}")
    stmt = (
        select(Day)
        .where(Day.user_id == user_id)
        .options(selectinload(Day.learning_progresses).selectinload(LearningProgress.learning_item))
        .order_by(func.random())
        .limit(1)
    )

    if timestamp_start:
        stmt = stmt.where(Day.timestamp >= timestamp_start)
    if timestamp_end:
        stmt = stmt.where(Day.timestamp <= timestamp_end)

    result = await db.execute(stmt)
    day = result.scalar_one_or_none()

    if not day:
        raise HTTPException(status_code=404, detail="No days found in the given time range")

    return Msg(code=200, msg="Random day retrieved", data=DayDetail.model_validate(day))


@router.get("/{timestamp}", response_model=Msg[DayDetail])
async def get_day(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    timestamp: int,
) -> Msg[DayDetail]:
    stmt = (
        select(Day)
        .where(Day.user_id == user_id, Day.timestamp == timestamp)
        .options(selectinload(Day.learning_progresses).selectinload(LearningProgress.learning_item))
    )

    result = await db.execute(stmt)
    day = result.scalar_one_or_none()

    if not day:
        raise HTTPException(status_code=404, detail="Day not found")

    return Msg(code=200, msg="Day retrieved", data=DayDetail.model_validate(day))


@router.post("/{timestamp}", response_model=Msg[None])
async def create_day(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    timestamp: int,
    data: DayCreate,
) -> Msg[None]:
    exists_stmt = select(exists().where(Day.timestamp == timestamp, Day.user_id == user_id))
    exists_result = await db.execute(exists_stmt)
    exists_day = exists_result.scalar_one_or_none()
    if exists_day:
        raise HTTPException(status_code=404, detail="Day already exists")

    city_exists = await db.scalar(select(exists().where(City.id == data.city_id)))
    if not city_exists:
        raise HTTPException(status_code=404, detail="City not found")

    learning_item_ids = {progress.learning_item_id for progress in data.learning_progresses}
    if learning_item_ids:
        stmt = select(func.count()).where(LearningItem.id.in_(learning_item_ids))
        result = await db.execute(stmt)
        found_count = result.scalar()

        if found_count != len(learning_item_ids):
            raise HTTPException(status_code=404, detail="One or more learning items not found")

    db.add(Day(
        timestamp=timestamp,
        user_id=user_id,
        city_id=data.city_id,
        description=data.description,
        content=data.content,
        steps=data.steps,
        main_image=data.main_image,
        images=data.images,
        learning_progresses=[
            LearningProgress(
                user_id=user_id,
                timestamp=timestamp,
                learning_item_id=progress.learning_item_id,
                time_involved=progress.time_involved,
            ) for progress in data.learning_progresses
        ],
    ))
    await db.commit()

    return Msg(code=201, msg="Day created")


@router.patch("/{timestamp}/toggle-starred", response_model=Msg[None])
async def toggle_starred(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    timestamp: int,
) -> Msg[None]:
    day: Day | None = await db.get(Day, (timestamp, user_id))
    if not day:
        raise HTTPException(status_code=404, detail="Day not found")

    day.starred = not day.starred
    await db.commit()
    return Msg(code=200, msg="Day updated")


@router.put("/{timestamp}", response_model=Msg[None])
async def update_day(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    timestamp: int,
    data: DayUpdate,
) -> Msg[None]:
    day: Day | None = await db.get(Day, (timestamp, user_id))
    if not day:
        raise HTTPException(status_code=404, detail="Day not found")

    update_data = data.model_dump(exclude_unset=True)
    learning_progresses = update_data.pop('learning_progresses', None)

    if update_data:
        stmt = (
            update(Day)
            .where(Day.user_id == user_id, Day.timestamp == timestamp)
            .values(**update_data)
        )
        await db.execute(stmt)

    if learning_progresses:
        await db.execute(
            delete(LearningProgress).where(
                LearningProgress.user_id == user_id,
                LearningProgress.timestamp == timestamp,
            )
        )

        for progress in learning_progresses:
            new_progress = LearningProgress(
                user_id=user_id,
                timestamp=timestamp,
                learning_item_id=progress["learning_item_id"],
                time_involved=progress["time_involved"]
            )
            db.add(new_progress)

    await db.commit()
    return Msg(code=200, msg="Day updated")



# ???
# @router.delete("/{timestamp}", response_model=Msg[None])
# async def delete_day(
#     db: Annotated[AsyncSession, Depends(get_db)],
#     user_id: Annotated[UUID, Depends(get_current_user())],
#     timestamp: int,
# ) -> Msg[None]:
#     stmt = delete(Day).where(Day.user_id == user_id, timestamp == timestamp)
#     await db.execute(stmt)
#     await db.commit()

#     return Msg(code=200, msg="Day deleted")

