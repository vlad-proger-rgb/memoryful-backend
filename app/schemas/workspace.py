from uuid import UUID

from fastapi_camelcase import CamelModel

from app.enums import WorkspacePage
from app.schemas.media import ResolvedBackground


class PageBackgroundIn(CamelModel):
    """A page's background as the client sets it. `key=None` clears the page."""

    key: str | None = None
    placeholder: str | None = None


class WorkspaceUpdate(CamelModel):
    """Only the pages present are touched; the rest are left alone."""

    backgrounds: dict[WorkspacePage, PageBackgroundIn]


class WorkspaceInDB(CamelModel):
    user_id: UUID
    # Only customized pages appear. The client supplies its own defaults.
    backgrounds: dict[WorkspacePage, ResolvedBackground]
