from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, exists, update, delete, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import TrackableItem, TrackableType
from app.core.deps import get_current_user
from app.schemas import Msg
from app.schemas.trackable import (
    TrackableDetail,
    TrackableInDB,
    TrackableCreate,
    TrackableUpdate,
)

router = APIRouter(
    prefix="/trackables",
    tags=["Trackables"],
)


@router.get("/", response_model=Msg[list[TrackableInDB]])
async def get_trackables(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    type_id: UUID | None = Query(None, description="Trackable type ID", alias="typeId"),
    search: str | None = Query(None, description="Search query"),
) -> Msg[list[TrackableInDB]]:
    stmt = select(TrackableItem).where(TrackableItem.user_id == user_id)

    if type_id:
        stmt = stmt.where(TrackableItem.type_id == type_id)

    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            or_(
                TrackableItem.title.ilike(search_term),
                TrackableItem.description.ilike(search_term) if TrackableItem.description is not None else False,
            )
        )

    trackables = await db.scalars(stmt)
    return Msg(
        code=200, 
        msg="Trackable items retrieved", 
        data=[TrackableInDB.model_validate(t) for t in trackables],
    )


@router.get("/{id}", response_model=Msg[TrackableDetail])
async def get_trackable(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    id: UUID,
) -> Msg[TrackableDetail]:
    stmt = select(TrackableItem).where(
        TrackableItem.id == id, 
        TrackableItem.user_id == user_id,
    ).options(
        selectinload(TrackableItem.type),
    )
    trackable = await db.scalar(stmt)
    if not trackable:
        raise HTTPException(404, "Trackable item not found")

    return Msg(code=200, msg="Trackable item retrieved", data=TrackableDetail.model_validate(trackable))


@router.post("/", response_model=Msg[UUID])
async def create_trackable(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    data: TrackableCreate,
) -> Msg[UUID]:
    type_stmt = select(TrackableType).where(
        TrackableType.id == data.type_id,
        TrackableType.user_id == user_id,
    )
    type_result = await db.scalar(type_stmt)
    if not type_result:
        raise HTTPException(404, "Trackable type not found")

    exists_stmt = select(exists().where(
        TrackableItem.title == data.title,
        TrackableItem.user_id == user_id,
    ))
    exists_result = await db.execute(exists_stmt)
    if exists_result.scalar_one_or_none():
        raise HTTPException(409, "Trackable item with the same title already exists")

    trackable = TrackableItem(**data.model_dump(), user_id=user_id)
    db.add(trackable)
    await db.commit()
    await db.refresh(trackable)

    return Msg(code=200, msg="Trackable item created", data=trackable.id)


@router.put("/{id}", response_model=Msg[None])
async def update_trackable(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    data: TrackableUpdate,
    id: UUID,
) -> Msg[None]:
    stmt = select(exists().where(
        TrackableItem.id == id, 
        TrackableItem.user_id == user_id,
    ))
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Trackable item not found")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return Msg(code=200, msg="No changes detected")

    if "type_id" in update_data:
        type_stmt = select(TrackableType).where(
            TrackableType.id == update_data["type_id"],
            TrackableType.user_id == user_id,
        )
        type_result = await db.scalar(type_stmt)
        if not type_result:
            raise HTTPException(404, "Trackable type not found")

    await db.execute(
        update(TrackableItem)
        .where(TrackableItem.id == id, TrackableItem.user_id == user_id)
        .values(**update_data)
    )
    await db.commit()

    return Msg(code=200, msg="Trackable item updated")


@router.delete("/{id}", response_model=Msg[None])
async def delete_trackable(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    id: UUID,
) -> Msg[None]:
    stmt = delete(TrackableItem).where(
        TrackableItem.id == id, 
        TrackableItem.user_id == user_id,
    )
    result = await db.execute(stmt)
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(404, "Trackable item not found")

    return Msg(code=200, msg="Trackable item deleted")
