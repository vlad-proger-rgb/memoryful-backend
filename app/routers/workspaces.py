from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Workspace
from app.schemas import Msg
from app.schemas.workspace import WorkspaceBase, WorkspaceInDB
from app.core.settings import (
    DEFAULT_DASHBOARD_BACKGROUND,
    DEFAULT_DAY_BACKGROUND,
    DEFAULT_SEARCH_BACKGROUND,
    DEFAULT_SETTINGS_BACKGROUND,
)


router = APIRouter(
    prefix="/workspaces",
    tags=["Workspaces"],
)


async def _get_workspace(db: AsyncSession, user_id: UUID) -> Workspace | None:
    return await db.scalar(select(Workspace).where(Workspace.user_id == user_id))


def _effective_workspace(user_id: UUID, ws: Workspace | None) -> WorkspaceInDB:
    return WorkspaceInDB(
        user_id=user_id,
        dashboard_background=(ws.dashboard_background if ws and ws.dashboard_background is not None else DEFAULT_DASHBOARD_BACKGROUND),
        day_background=(ws.day_background if ws and ws.day_background is not None else DEFAULT_DAY_BACKGROUND),
        search_background=(ws.search_background if ws and ws.search_background is not None else DEFAULT_SEARCH_BACKGROUND),
        settings_background=(
            ws.settings_background if ws and ws.settings_background is not None else DEFAULT_SETTINGS_BACKGROUND
        ),
    )


@router.get("/me", response_model=Msg[WorkspaceInDB])
async def get_my_workspace(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
) -> Msg[WorkspaceInDB]:
    ws = await _get_workspace(db, user_id)
    return Msg(code=200, msg="Workspace retrieved", data=_effective_workspace(user_id, ws))


@router.put("/me", response_model=Msg[WorkspaceInDB])
async def update_my_workspace(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    body: WorkspaceBase,
) -> Msg[WorkspaceInDB]:
    payload = body.model_dump(exclude_unset=True)
    ws = await _get_workspace(db, user_id)

    if ws is None:
        if any(v is not None for v in payload.values()):
            ws = Workspace(
                user_id=user_id,
                dashboard_background=None,
                day_background=None,
                search_background=None,
                settings_background=None,
            )
            db.add(ws)
        else:
            return Msg(code=200, msg="Workspace updated", data=_effective_workspace(user_id, None))

    for k, v in payload.items():
        setattr(ws, k, v)

    all_null = (
        ws.dashboard_background is None
        and ws.day_background is None
        and ws.search_background is None
        and ws.settings_background is None
    )

    if all_null:
        await db.delete(ws)
        await db.commit()
        return Msg(code=200, msg="Workspace updated", data=_effective_workspace(user_id, None))

    await db.commit()
    await db.refresh(ws)
    return Msg(code=200, msg="Workspace updated", data=_effective_workspace(user_id, ws))
