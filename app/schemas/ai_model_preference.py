from uuid import UUID

from fastapi_camelcase import CamelModel

from app.schemas.chat_model import ChatModelRef


class PurposeModelIn(CamelModel):
    model_id: UUID | None


class PurposeModel(CamelModel):
    model: ChatModelRef
    is_default: bool
