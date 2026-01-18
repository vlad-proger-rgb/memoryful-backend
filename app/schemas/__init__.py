from pydantic import BaseModel

from .chat_model import ChatModelInDB
from .chat import (
    ChatCreate,
    ChatUpdate,
    ChatListItem,
    ChatDetail,
    MessageSchema,
)
from .insight import InsightInDB
from .suggestion import SuggestionInDB
from .city import CityInDB, CityDetail
from .country import CountryInDB
from .day import DayCreate, DayUpdate, DayListItem, DayDetail, DayFilters
from .email import Email, EmailSchema, VerifyCodeForm
from .month import MonthBase, MonthInDB
from .storage import PresignGetRequest, PresignGetResponse, PresignPutRequest, PresignPutResponse
from .security import Token, AuthResponse, Session
from .tag import TagBase, TagInDB
from .trackable import (
    TrackableBase,
    TrackableCreate,
    TrackableUpdate,
    TrackableInDB,
)
from .trackable_type import TrackableTypeInDB
from .day_trackable_progress import DayTrackableProgress, DayTrackableProgressUpdate, TrackableTypeWithProgress
from .user import UserBase, UserInDB
from .workspace import WorkspaceBase, WorkspaceInDB
from .font_awesome import FAIcon


__all__ = [
    "Msg",
    "ChatModelInDB",
    "ChatCreate",
    "ChatUpdate",
    "ChatListItem",
    "ChatDetail",
    "MessageSchema",
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
    "WorkspaceBase",
    "WorkspaceInDB",
]

class Msg[T](BaseModel):
    code: int | None = None
    msg: str | None = None
    data: T | None = None
