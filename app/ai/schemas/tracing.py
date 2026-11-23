import datetime as dt
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field, field_serializer

from app.enums import AiRunTrigger, AiUsagePurpose
from app.models import ChatModel


class AiRunMetadata(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    model: ChatModel
    user_id: UUID
    purpose: AiUsagePurpose
    trigger: AiRunTrigger
    chat_id: UUID | None = None
    streamed: bool | None = None
    day: dt.date | None = None
    week: dt.date | None = None
    days_missing_ai: int | None = None
    agent_failed: bool | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def thread_id(self) -> UUID | None:
        # LangSmith's Threads view groups traces by this key.
        return self.chat_id

    @field_serializer("model")
    def _model_slug(self, model: ChatModel) -> str | None:
        return model.slug
