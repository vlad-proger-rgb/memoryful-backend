from pydantic import BaseModel

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
from .chat_model import ChatModelInDB
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
from .security import AuthResponse, Session, Token
from .storage import PresignGetRequest, PresignGetResponse, PresignPutRequest, PresignPutResponse
from .suggestion import SuggestionInDB
from .tag import TagBase, TagInDB
from .trackable import (
    TrackableBase,
    TrackableCreate,
    TrackableInDB,
    TrackableUpdate,
)
from .trackable_type import TrackableTypeInDB
from .user import UserBase, UserInDB
from .workspace import (
    PageBackgroundIn,
    WorkspaceInDB,
    WorkspaceUpdate,
)

__all__ = [
    "Msg",
    "ChatModelInDB",
    "ChatCreate",
    "ChatUpdate",
    "ChatListItem",
    "ChatDetail",
    "MessageSchema",
    "ToolCallSchema",
    "CompletionCreate",
    "CompletionResponse",
    "InsightInDB",
    "SuggestionInDB",
    "CityInDB",
    "CityDetail",
    "CountryInDB",
    "DayCreate",
    "DayUpdate",
    "DayListItem",
    "DayDetail",
    "DayFilters",
    "Email",
    "EmailSchema",
    "FAIcon",
    "VerifyCodeForm",
    "MonthBase",
    "MonthInDB",
    "PresignGetRequest",
    "PresignGetResponse",
    "PresignPutRequest",
    "PresignPutResponse",
    "Token",
    "AuthResponse",
    "Session",
    "TagBase",
    "TagInDB",
    "TrackableBase",
    "TrackableCreate",
    "TrackableUpdate",
    "TrackableInDB",
    "TrackableTypeInDB",
    "DayTrackableProgress",
    "DayTrackableProgressUpdate",
    "TrackableTypeWithProgress",
    "UserBase",
    "UserInDB",
    "ResolvedBackground",
    "PageBackgroundIn",
    "WorkspaceInDB",
    "WorkspaceUpdate",
]


class Msg[T](BaseModel):
    code: int | None = None
    msg: str | None = None
    data: T | None = None
