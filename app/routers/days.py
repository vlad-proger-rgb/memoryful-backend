from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Query,
)
from pydantic import ValidationError
from sqlalchemy import select, update, delete, exists, func, and_
from sqlalchemy.sql import Select
from sqlalchemy.orm import selectinload, load_only
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Day, City, Tag, TrackableItem, TrackableProgress
from app.core.deps import get_current_user
from app.enums.sorting import SortOrder, DaySortField
from app.schemas import (
    Msg,
    DayListItem,
    DayDetail,
    DayCreate,
    DayUpdate,
    DayFilters,
    DayTrackableProgress,
    TrackableTypeWithProgress,
)
from app.schemas.trackable_type import TrackableTypeInDB


router = APIRouter(
    prefix="/days",
    tags=["Days"],
)


def _apply_filters(stmt: Select, filters: DayFilters | None, tag_names: list[str] | None = None, user_id: UUID | None = None) -> Select:
    if tag_names:
        # Subquery: find days that have ALL the specified tags
        tag_subquery = (
            select(Day.timestamp, Day.user_id)
            .join(Day.tags)
            .where(Tag.name.in_(tag_names))
        )
        if user_id:
            tag_subquery = tag_subquery.where(Tag.user_id == user_id)
        tag_subquery = (
            tag_subquery
            .group_by(Day.timestamp, Day.user_id)
            .having(func.count(Tag.id) == len(tag_names))
            .subquery()
        )
        stmt = stmt.where(
            and_(
                Day.timestamp == tag_subquery.c.timestamp,
                Day.user_id == tag_subquery.c.user_id
            )
        )

    if not filters:
        return stmt

    conditions = []

    if filters.starred is not None:
        conditions.append(Day.starred == filters.starred)
    if filters.city_id is not None:
        conditions.append(Day.city_id == filters.city_id)
    if filters.country_id is not None:
        conditions.append(Day.city.has(City.country_id == filters.country_id))
    if filters.created_after is not None:
        conditions.append(Day.timestamp >= filters.created_after)
    if filters.created_before is not None:
        conditions.append(Day.timestamp <= filters.created_before)

    if filters.steps:
        for op, steps in filters.steps.items():
            if op == 'gt':
                conditions.append(Day.steps > steps)
            elif op == 'lt':
                conditions.append(Day.steps < steps)
            elif op == 'gte':
                conditions.append(Day.steps >= steps)
            elif op == 'lte':
                conditions.append(Day.steps <= steps)
            elif op == 'eq':
                conditions.append(Day.steps == steps)
            elif op == 'ne':
                conditions.append(Day.steps != steps)

    if filters.description:
        for op, description in filters.description.items():
            if op == 'like':
                conditions.append(Day.description.ilike(f'%{description}%'))
            elif op == 'eq':
                conditions.append(Day.description == description)
            elif op == 'ne':
                conditions.append(Day.description != description)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    return stmt


def _apply_sorting(stmt: Select, sort_field: DaySortField | None, sort_order: SortOrder = SortOrder.DESC) -> Select:
    if not sort_field:
        return stmt.order_by(Day.timestamp.desc())

    field = getattr(Day, sort_field.value, None)
    if not field:
        return stmt

    if sort_order == SortOrder.ASC:
        return stmt.order_by(field.asc())
    return stmt.order_by(field.desc())


@router.get("/", response_model=Msg[list[DayListItem | DayDetail]])
async def get_days(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    limit: int = Query(None, ge=1, le=100, description="Number of items to return"),
    offset: int = Query(None, ge=0, description="Number of items to skip"),
    sort_field: DaySortField | None = Query(
        None,
        description="Field to sort by",
        alias="sortField",
    ),
    sort_order: SortOrder = Query(
        SortOrder.DESC,
        description="Sort order (asc/desc)",
        alias="sortOrder",
    ),
    view: Literal["list", "detail"] = Query(
        "list",
        description="View type to return. 'list' returns minimal data, 'detail' includes all relationships",
        alias="view",
    ),
    tag_names: str | None = Query(
        None,
        description="Comma-separated list of tag names to filter by",
        alias="tagNames",
    ),
    filters: str | None = Query(
        None,
        description=DayFilters.__doc__,
        alias="filters",
    ),
) -> Msg[list[DayListItem | DayDetail]]:
    """
    Get a list of days with optional filtering and sorting.

    Examples:
    - Basic usage: /days/
    - With filters: /days/?filters={"starred":true,"steps":{"gt":5000}}
    - With tags: /days/?tag_names=work,travel
    - With sorting: /days/?sort_field=timestamp&sort_order=desc
    """

    try:
        filter_params = DayFilters.model_validate_json(filters) if filters else None
    except ValidationError as e:
        raise HTTPException(400, f"Invalid filters: {str(e)}")

    tag_name_list = [
        name.strip() 
        for name in (tag_names.split(",") if tag_names else []) 
        if name.strip()
    ]

    stmt = select(Day).where(Day.user_id == user_id)

    stmt = _apply_filters(stmt, filter_params, tag_name_list if tag_name_list else None, user_id)
    stmt = _apply_sorting(stmt, sort_field, sort_order)

    if limit is not None:
        stmt = stmt.limit(limit)

    if offset is not None:
        stmt = stmt.offset(offset)

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
            selectinload(Day.trackable_progresses)
                .selectinload(TrackableProgress.trackable_item)
                .selectinload(TrackableItem.type),
        )
    else:
        stmt = stmt.options(
            selectinload(Day.tags),
            selectinload(Day.city)
                .selectinload(City.country),
            selectinload(Day.trackable_progresses)
                .selectinload(TrackableProgress.trackable_item)
                .selectinload(TrackableItem.type),
        )

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
    stmt = (
        select(Day)
        .where(Day.user_id == user_id)
        .options(
            selectinload(Day.tags),
            selectinload(Day.city)
                .selectinload(City.country),
            selectinload(Day.trackable_progresses)
                .selectinload(TrackableProgress.trackable_item)
                .selectinload(TrackableItem.type),
        )
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
        raise HTTPException(404, "No days found in the given time range")

    return Msg(code=200, msg="Random day retrieved", data=DayDetail.model_validate(day))


@router.get("/{timestamp}", response_model=Msg[DayDetail])
async def get_day(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    timestamp: int,
) -> Msg[DayDetail]:
    stmt = (
        select(Day)
        .options(
            selectinload(Day.tags),
            selectinload(Day.city)
                .selectinload(City.country),
            selectinload(Day.trackable_progresses)
                .selectinload(TrackableProgress.trackable_item)
                .selectinload(TrackableItem.type),
        )
        .where(Day.timestamp == timestamp, Day.user_id == user_id)
    )
    day = await db.scalar(stmt)
    if not day:
        raise HTTPException(404, "Day not found")

    from collections import defaultdict

    progresses_by_type = defaultdict(list)
    type_objects = {}

    for progress in day.trackable_progresses:
        trackable_type = progress.trackable_item.type
        type_objects[trackable_type.id] = TrackableTypeInDB.model_validate(trackable_type)
        progresses_by_type[trackable_type.id].append(DayTrackableProgress.model_validate(progress))

    trackable_progresses = [
        TrackableTypeWithProgress(
            type=type_objects[type_id],
            progresses=progresses
        )
        for type_id, progresses in progresses_by_type.items()
    ]

    day_data = {
        **{k: v for k, v in day.__dict__.items() if not k.startswith('_')},
        "trackable_progresses": trackable_progresses,
    }
    print(f"DAYS {day_data=}")

    day_schema = DayDetail.model_validate(day_data)

    return Msg(code=200, msg="Day retrieved", data=day_schema)


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
        raise HTTPException(404, "Day already exists")

    city_exists = await db.scalar(select(exists().where(City.id == data.city_id)))
    if not city_exists:
        raise HTTPException(404, "City not found")

    if data.trackable_progresses:
        trackable_item_ids = {progress.trackable_item_id for progress in data.trackable_progresses}
        stmt = select(func.count()).where(
            TrackableItem.id.in_(trackable_item_ids),
            TrackableItem.user_id == user_id,
        )
        result = await db.execute(stmt)
        found_count = result.scalar()

        if found_count != len(trackable_item_ids):
            raise HTTPException(404, "One or more trackable items not found")

    db.add(Day(
        timestamp=timestamp,
        user_id=user_id,
        city_id=data.city_id,
        description=data.description,
        content=data.content,
        steps=data.steps,
        main_image=data.main_image,
        images=data.images,
        trackable_progresses=[
            TrackableProgress(
                user_id=user_id,
                timestamp=timestamp,
                trackable_item_id=progress.trackable_item_id,
                value=progress.value,
            ) for progress in data.trackable_progresses
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
        raise HTTPException(404, "Day not found")

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
    print(f"UPDATE DAY {data=}")

    day_result = await db.execute(
        select(Day).options(selectinload(Day.tags)).where(Day.timestamp == timestamp, Day.user_id == user_id)
    )
    day: Day | None = day_result.scalar_one_or_none()
    if not day:
        raise HTTPException(404, "Day not found")

    update_data = data.model_dump(exclude_unset=True)
    trackable_progresses = update_data.pop('trackable_progresses', None)
    tag_uuids = update_data.pop('tags', None)

    if update_data:
        stmt = (
            update(Day)
            .where(Day.user_id == user_id, Day.timestamp == timestamp)
            .values(**update_data)
        )
        await db.execute(stmt)

    if tag_uuids is not None:
        tags = []
        if tag_uuids:
            tags_result = await db.execute(select(Tag).where(Tag.id.in_(tag_uuids)))
            tags = list(tags_result.scalars().unique())
            if len(tags) != len(tag_uuids):
                raise HTTPException(404, "One or more tags not found")
        day.tags.clear()
        day.tags.extend(tags)

    if trackable_progresses is not None:
        await db.execute(
            delete(TrackableProgress).where(
                TrackableProgress.user_id == user_id,
                TrackableProgress.timestamp == timestamp,
            )
        )

        for progress in trackable_progresses:
            new_progress = TrackableProgress(
                user_id=user_id,
                timestamp=timestamp,
                trackable_item_id=progress["trackable_item_id"],
                value=progress["value"],
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

