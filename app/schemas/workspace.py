from uuid import UUID

from pydantic import ConfigDict
from fastapi_camelcase import CamelModel


class WorkspaceBase(CamelModel):
    dashboard_background: str | None = None
    day_background: str | None = None
    search_background: str | None = None
    settings_background: str | None = None


class WorkspaceInDB(WorkspaceBase):
    model_config = ConfigDict(from_attributes=True)
    user_id: UUID
