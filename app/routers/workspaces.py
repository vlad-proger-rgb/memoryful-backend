from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cached, clear_cache
from app.core.database import get_db
from app.core.deps import StorageServiceDep, get_current_user
from app.core.settings import CACHE_TTL_USER_DATA
from app.core.storage.service import StorageService
from app.core.storage.utils import is_video_key
from app.enums import WorkspacePage
from app.models import WorkspaceBackground
from app.schemas import Msg, ResolvedBackground
from app.schemas.workspace import WorkspaceInDB, WorkspaceUpdate

router = APIRouter(
    prefix="/workspaces",
    tags=["Workspaces"],
)


async def _rows(
    db: AsyncSession,
    user_id: UUID,
) -> list[WorkspaceBackground]:
    result = await db.scalars(
        select(WorkspaceBackground).where(WorkspaceBackground.user_id == user_id)
    )
    return list(result)


async def _response(
    storage: StorageService,
    user_id: UUID,
    rows: list[WorkspaceBackground],
    msg: str,
) -> Msg[WorkspaceInDB]:
    known = {page.value for page in WorkspacePage}
    backgrounds = {
        row.page: ResolvedBackground(
            key=row.object_key,
            placeholder=row.placeholder,
            url=await storage.resolve_url(user_id, row.object_key),
            is_video=is_video_key(row.object_key),
        )
        for row in rows
        if row.page in known
    }  # fmt: skip
    return Msg(
        code=200,
        msg=msg,
        data=WorkspaceInDB(user_id=user_id, backgrounds=backgrounds),
    )


@router.get("/me", response_model=Msg[WorkspaceInDB])
@cached(expire=CACHE_TTL_USER_DATA, namespace="workspaces")
async def get_my_workspace(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    storage_service: StorageServiceDep,
) -> Msg[WorkspaceInDB]:
    rows = await _rows(db, user_id)
    return await _response(storage_service, user_id, rows, "Workspace retrieved")


@router.put("/me", response_model=Msg[WorkspaceInDB])
async def update_my_workspace(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    body: WorkspaceUpdate,
    storage_service: StorageServiceDep,
    background_tasks: BackgroundTasks,
) -> Msg[WorkspaceInDB]:
    existing = {row.page: row for row in await _rows(db, user_id)}
    orphaned: set[str] = set()

    for page, background in body.backgrounds.items():
        row = existing.get(page)

        if row is not None and row.object_key != background.key:
            orphaned.add(row.object_key)

        if background.key is None:
            if row is not None:
                await db.delete(row)
            continue

        if row is None:
            db.add(
                WorkspaceBackground(
                    user_id=user_id,
                    page=page,
                    object_key=background.key,
                    placeholder=background.placeholder,
                )
            )
        else:
            row.object_key = background.key
            row.placeholder = background.placeholder

    await db.commit()
    await clear_cache("workspaces")
    background_tasks.add_task(storage_service.delete_objects, user_id, orphaned)

    return await _response(storage_service, user_id, await _rows(db, user_id), "Workspace updated")
