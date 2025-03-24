import json
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Query,
)
from sqlalchemy import select, update, delete, exists, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Day, City, LearningItem, LearningProgress
from app.core.deps import get_current_user
from app.schemas import (
    Msg,
    DayInDB as D,
    DayCreate,
    DayUpdate,
)


router = APIRouter(
    prefix="/days",
    tags=["Days"],
)


@router.get("/", response_model=Msg[list[D]])
async def get_days(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str | None = Query(None),
    fields: list[str] | None = Query(None),
    filters: str | None = Query(None),
    # origin: str | None = Query(None),  # TODO: from where the request comes? calendar/search/chat - ?
) -> Msg[list[D]]:
    selected_columns = [getattr(Day, field) for field in fields] if fields else [Day]
    stmt = (
        select(*selected_columns)
        .where(Day.user_id == user_id)
        .options(selectinload(Day.learning_progresses))
    )

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

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)

    if fields:
        days = result.fetchall()
    else:
        days: list[Day] = list(result.scalars())

    return Msg(code=200, msg="Days retrieved", data=days)


@router.get("/{timestamp}", response_model=Msg[D])
async def get_day(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    timestamp: int,
    fields: str | None = Query(None),
) -> Msg[D]:
    selected_columns = [getattr(Day, field) for field in fields] if fields else [Day]
    stmt = (
        select(*selected_columns)
        .where(Day.user_id == user_id, Day.timestamp == timestamp)
        .options(selectinload(Day.learning_progresses))
    )

    result = await db.execute(stmt)
    day: Day = result.scalar_one_or_none()
    if not day:
        raise HTTPException(status_code=404, detail="Day not found")

    return Msg(code=200, msg="Day retrieved", data=day)


@router.get("/random/{timestamp}", response_model=Msg[D])
async def get_random_day(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    timestamp_start: int,
    timestamp_end: int,
    fields: str | None = Query(None),
) -> Msg[D]:
    pass


@router.post("/{timestamp}", response_model=Msg[None])
async def create_day(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    data: DayCreate,
) -> Msg[None]:
    stmt = select(exists().where(City.id == data.city_id))
    result = await db.execute(stmt)
    if not result.scalar():
        raise HTTPException(status_code=404, detail="City not found")

    learning_item_ids = {progress.learning_item_id for progress in data.learning_progresses}
    if learning_item_ids:
        stmt = select(func.count()).where(LearningItem.id.in_(learning_item_ids))
        result = await db.execute(stmt)
        found_count = result.scalar()

        if found_count != len(learning_item_ids):
            raise HTTPException(status_code=404, detail="One or more learning items not found")

    db.add(Day(
        timestamp=data.timestamp,
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
                timestamp=data.timestamp,
                learning_item_id=progress.learning_item_id,
                time_involved=progress.time_involved,
            ) for progress in data.learning_progresses
        ],
    ))
    await db.commit()

    return Msg(code=201, msg="Day created")


@router.put("/{timestamp}", response_model=Msg[None])
async def update_day(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    timestamp: int,
    data: DayUpdate,
) -> Msg[None]:
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
        day = await db.get(Day, (timestamp, user_id))
        if not day:
            raise HTTPException(status_code=404, detail="Day not found")

        stmt = delete(LearningProgress).where(
            LearningProgress.user_id == user_id,
            LearningProgress.timestamp == timestamp,
        )
        await db.execute(stmt)

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

