from pydantic import BaseModel

from .ai_model_preference import PurposeModel, PurposeModelIn
from .chat import (
    ChatCreate,
    ChatDetail,
    ChatListItem,
    ChatUpdate,
    CompletionCreate,
    CompletionResponse,
    MessageSchema,
    ToolCallSchema,
)
from .chat_model import ChatModelInDB, ChatModelRef
from .city import CityDetail, CityInDB
from .country import CountryInDB
from .day import DayCreate, DayDetail, DayFilters, DayListItem, DayUpdate
from .day_trackable_progress import (
    DayTrackableProgress,
    DayTrackableProgressUpdate,
    TrackableTypeWithProgress,
)
from .email import Email, EmailSchema, VerifyCodeForm
from .font_awesome import FAIcon
from .insight import InsightInDB
from .media import ResolvedBackground
from .month import MonthBase, MonthInDB
from .security import AuthResponse, GoogleCredential, GoogleNonce, Session, Token
from .storage import PresignGetRequest, PresignGetResponse, PresignPutRequest, PresignPutResponse
from .tag import TagBase, TagInDB
from .trackable import (
    TrackableBase,
    TrackableCreate,
    TrackableInDB,
    TrackableUpdate,
)
from .trackable_type import TrackableTypeInDB
from .user import UserBase, UserInDB
from .week_digest import WeekDigestInDB, WeekDigestSection
from .workspace import (
    PageBackgroundIn,
    WorkspaceInDB,
    WorkspaceUpdate,
)

__all__ = [
    "AuthResponse",
    "ChatCreate",
    "ChatDetail",
    "ChatListItem",
    "ChatModelInDB",
    "ChatModelRef",
    "ChatUpdate",
    "CityDetail",
    "CityInDB",
    "CompletionCreate",
    "CompletionResponse",
    "CountryInDB",
    "DayCreate",
    "DayDetail",
    "DayFilters",
    "DayListItem",
    "DayTrackableProgress",
    "DayTrackableProgressUpdate",
    "DayUpdate",
    "Email",
    "EmailSchema",
    "FAIcon",
    "GoogleCredential",
    "GoogleNonce",
    "InsightInDB",
    "MessageSchema",
    "MonthBase",
    "MonthInDB",
    "Msg",
    "PageBackgroundIn",
    "PresignGetRequest",
    "PresignGetResponse",
    "PresignPutRequest",
    "PresignPutResponse",
    "PurposeModel",
    "PurposeModelIn",
    "ResolvedBackground",
    "Session",
    "TagBase",
    "TagInDB",
    "Token",
    "ToolCallSchema",
    "TrackableBase",
    "TrackableCreate",
    "TrackableInDB",
    "TrackableTypeInDB",
    "TrackableTypeWithProgress",
    "TrackableUpdate",
    "UserBase",
    "UserInDB",
    "VerifyCodeForm",
    "WeekDigestInDB",
    "WeekDigestSection",
    "WorkspaceInDB",
    "WorkspaceUpdate",
]


class Msg[T](BaseModel):
    code: int | None = None
    msg: str | None = None
    data: T | None = None
