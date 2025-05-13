from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
)
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Tag
from app.core.deps import get_current_user
from app.schemas import (
    Msg,
    TagInDB as T,
    TagBase,
)


router = APIRouter(
    prefix="/tags",
    tags=["Tags"],
)


@router.get("/", response_model=Msg[list[T]])
async def get_tags(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
) -> Msg[list[T]]:
    stmt = select(Tag).where(Tag.user_id == user_id)
    tags = await db.scalars(stmt)

    return Msg(code=200, msg="Tags retrieved", data=[T.model_validate(t) for t in tags])


# ???
@router.get("/{id}", response_model=Msg[T])
async def get_tag(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    id: UUID,
) -> Msg[T]:
    stmt = select(Tag).where(Tag.id == id, Tag.user_id == user_id)
    tag = await db.scalar(stmt)
    if not tag:
        raise HTTPException(404, "Tag not found")

    return Msg(code=200, msg="Tag retrieved", data=T.model_validate(tag))


@router.post("/", response_model=Msg[UUID])
async def create_tag(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    data: TagBase,
) -> Msg[UUID]:
    tag = Tag(**data.model_dump(), user_id=user_id)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)

    return Msg(code=200, msg="Tag created", data=tag.id)


@router.put("/{id}", response_model=Msg[None])
async def update_tag(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    data: TagBase,
    id: UUID,
) -> Msg[None]:
    stmt = (
        update(Tag)
        .where(Tag.id == id, Tag.user_id == user_id)
        .values(**data.model_dump())
    )
    await db.execute(stmt)
    await db.commit()

    return Msg(code=200, msg="Tag updated")


@router.delete("/{id}",response_model=Msg[None])
async def delete_tag(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    id: UUID,
) -> Msg[None]:
    stmt = delete(Tag).where(Tag.id == id, Tag.user_id == user_id)
    await db.execute(stmt)
    await db.commit()

    return Msg(code=200, msg="Tag deleted")

