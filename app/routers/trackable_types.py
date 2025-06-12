from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import TrackableType
from app.schemas import Msg
from app.schemas.trackable_type import TrackableTypeInDB

router = APIRouter(
    prefix="/trackable-types",
    tags=["Trackable types"],
)


@router.get("/", response_model=Msg[list[TrackableTypeInDB]])
async def get_trackable_types(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Msg[list[TrackableTypeInDB]]:
    stmt = select(TrackableType)
    trackable_types = await db.scalars(stmt)
    return Msg(
        code=200,
        msg="Trackable types retrieved",
        data=[TrackableTypeInDB.model_validate(t) for t in trackable_types],
    )


@router.get("/{id}", response_model=Msg[TrackableTypeInDB])
async def get_trackable_type(
    db: Annotated[AsyncSession, Depends(get_db)],
    id: UUID,
) -> Msg[TrackableTypeInDB]:
    stmt = select(TrackableType).where(
        TrackableType.id == id,
    )
    trackable_type = await db.scalar(stmt)
    if not trackable_type:
        raise HTTPException(404, "Trackable type not found")

    return Msg( 
        code=200,
        msg="Trackable type retrieved",
        data=TrackableTypeInDB.model_validate(trackable_type),
    )
