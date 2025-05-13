from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
)
from sqlalchemy import select, exists, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import LearningItem
from app.core.deps import get_current_user
from app.schemas import (
    Msg,
    LearningItemInDB as L,
    LearningItemCreate,
)


router = APIRouter(
    prefix="/learning-items",
    tags=["Learning Items"],
)


@router.get("/", response_model=Msg[list[L]])
async def get_learning_items(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
) -> Msg[list[L]]:
    stmt = select(LearningItem).where(LearningItem.user_id == user_id)
    learning_items = await db.scalars(stmt)

    return Msg(code=200, msg="Learning Items retrieved", data=[L.model_validate(li) for li in learning_items])


@router.get("/{id}", response_model=Msg[L])
async def get_learning_item(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    id: UUID,
) -> Msg[L]:
    stmt = select(LearningItem).where(LearningItem.id == id, LearningItem.user_id == user_id)
    learning_item = await db.scalar(stmt)
    if not learning_item:
        raise HTTPException(404, "Learning Item not found")

    return Msg(code=200, msg="Learning Item retrieved", data=L.model_validate(learning_item))


@router.post("/", response_model=Msg[UUID])
async def create_learning_item(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    data: LearningItemCreate,
) -> Msg[UUID]:
    learning_item = LearningItem(**data.model_dump(), user_id=user_id)
    db.add(learning_item)
    await db.commit()
    await db.refresh(learning_item)

    return Msg(code=200, msg="Learning Item created", data=learning_item.id)


@router.put("/{id}", response_model=Msg[None])
async def update_learning_item(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    data: LearningItemCreate,
    id: UUID,
) -> Msg[None]:
    stmt = select(exists().where(LearningItem.id == id, LearningItem.user_id == user_id))
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Learning Item not found")

    await db.execute(
        update(LearningItem)
        .where(LearningItem.id == id)
        .values(**data.model_dump(exclude_unset=True))
    )
    await db.commit()

    return Msg(code=200, msg="Learning Item updated")


@router.delete("/{id}", response_model=Msg[None])
async def delete_learning_item(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    id: UUID,
) -> Msg[None]:
    stmt = delete(LearningItem).where(LearningItem.id == id, LearningItem.user_id == user_id)
    await db.execute(stmt)
    await db.commit()

    return Msg(code=200, msg="Learning Item deleted")
