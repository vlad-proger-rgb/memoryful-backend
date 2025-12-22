from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import TrackableType
from app.core.deps import get_current_user
from app.schemas import Msg
from app.schemas.trackable_type import TrackableTypeInDB, TrackableTypeCreate, TrackableTypeUpdate

router = APIRouter(
    prefix="/trackable-types",
    tags=["Trackable types"],
)


@router.get("/", response_model=Msg[list[TrackableTypeInDB]])
async def get_trackable_types(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
) -> Msg[list[TrackableTypeInDB]]:
    stmt = select(TrackableType).where(TrackableType.user_id == user_id)
    trackable_types = await db.scalars(stmt)
    return Msg(
        code=200,
        msg="Trackable types retrieved",
        data=[TrackableTypeInDB.model_validate(t) for t in trackable_types],
    )


@router.get("/{id}", response_model=Msg[TrackableTypeInDB])
async def get_trackable_type(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    id: UUID,
) -> Msg[TrackableTypeInDB]:
    stmt = select(TrackableType).where(
        TrackableType.id == id,
        TrackableType.user_id == user_id,
    )
    trackable_type = await db.scalar(stmt)
    if not trackable_type:
        raise HTTPException(404, "Trackable type not found")

    return Msg( 
        code=200,
        msg="Trackable type retrieved",
        data=TrackableTypeInDB.model_validate(trackable_type),
    )


@router.post("/", response_model=Msg[UUID])
async def create_trackable_type(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    data: TrackableTypeCreate,
) -> Msg[UUID]:
    trackable_type = TrackableType(user_id=user_id, **data.model_dump())
    db.add(trackable_type)
    await db.commit()
    await db.refresh(trackable_type)
    return Msg(code=200, msg="Trackable type created", data=trackable_type.id)


@router.put("/{id}", response_model=Msg[None])
async def update_trackable_type(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    data: TrackableTypeUpdate,
    id: UUID,
) -> Msg[None]:
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return Msg(code=200, msg="No changes detected")

    stmt = (
        update(TrackableType)
        .where(TrackableType.id == id, TrackableType.user_id == user_id)
        .values(**update_data)
    )
    result = await db.execute(stmt)
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(404, "Trackable type not found")

    return Msg(code=200, msg="Trackable type updated")


@router.delete("/{id}", response_model=Msg[None])
async def delete_trackable_type(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    id: UUID,
) -> Msg[None]:
    stmt = delete(TrackableType).where(TrackableType.id == id, TrackableType.user_id == user_id)
    result = await db.execute(stmt)
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(404, "Trackable type not found")

    return Msg(code=200, msg="Trackable type deleted")
