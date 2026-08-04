from fastapi_camelcase import CamelModel

from app.enums import StorageUploadIntent, WorkspacePage


class PresignPutRequest(CamelModel):
    intent: StorageUploadIntent
    filename: str
    content_type: str
    day_timestamp: int | None = None
    year: int | None = None
    month: int | None = None
    workspace_page_key: WorkspacePage | None = None


class PresignPutResponse(CamelModel):
    upload_url: str
    object_key: str


class PresignGetRequest(CamelModel):
    object_key: str


class PresignGetResponse(CamelModel):
    download_url: str
