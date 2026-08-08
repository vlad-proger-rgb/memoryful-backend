from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy import CursorResult, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import CACHE_TTL_USER_DATA
from app.core.cache import cached, clear_cache
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Tag
from app.models.day import days_tags
from app.schemas import (
    Msg,
    TagBase,
    TagInDB as T,
)

router = APIRouter(
    prefix="/tags",
    tags=["Tags"],
)


@router.get("/", response_model=Msg[list[T]])
@cached(expire=CACHE_TTL_USER_DATA, namespace="tags")
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

    await clear_cache("tags", user_id)
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
    )  # fmt: skip
    result = cast("CursorResult[Any]", await db.execute(stmt))
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(404, "Tag not found")

    await clear_cache("tags", user_id)
    # `DayDetail`/`DayBase` embed the full tag object by value, so cached
    # days would otherwise keep showing the old name/color/icon.
    await clear_cache("days_list", user_id)
    await clear_cache("days_detail", user_id)
    return Msg(code=200, msg="Tag updated")


@router.delete("/{id}", response_model=Msg[None])
async def delete_tag(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    id: UUID,
) -> Msg[None]:
    # days_tags has no ON DELETE CASCADE, and a bulk delete bypasses the ORM that
    # would otherwise clear the association rows.
    owned = select(Tag.id).where(Tag.id == id, Tag.user_id == user_id)
    await db.execute(delete(days_tags).where(days_tags.c.tag_id.in_(owned)))

    stmt = delete(Tag).where(Tag.id == id, Tag.user_id == user_id)
    result = cast("CursorResult[Any]", await db.execute(stmt))
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(404, "Tag not found")

    await clear_cache("tags", user_id)
    await clear_cache("days_list", user_id)
    await clear_cache("days_detail", user_id)
    return Msg(code=200, msg="Tag deleted")
