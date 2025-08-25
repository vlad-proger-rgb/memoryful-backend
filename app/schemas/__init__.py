from pydantic import BaseModel

from .chat_model import ChatModelInDB
from .chat import ChatCreate, ChatUpdate, ChatListItem, ChatDetail
from .city import CityInDB, CityDetail
from .country import CountryInDB
from .day import DayCreate, DayUpdate, DayListItem, DayDetail, DayFilters
from .email import Email, EmailSchema, VerifyCodeForm
from .month import MonthBase, MonthInDB
from .security import Token, AuthResponse, Session
from .tag import TagBase, TagInDB
from .trackable import (
    TrackableBase,
    TrackableCreate,
    TrackableUpdate,
    TrackableInDB,
)
from .day_trackable_progress import DayTrackableProgress, DayTrackableProgressUpdate, TrackableTypeWithProgress
from .user import UserBase, UserInDB
from .font_awesome import FAIcon


__all__ = [
    "Msg",
    "ChatModelInDB",
    "ChatCreate",
    "ChatUpdate",
    "ChatListItem",
    "ChatDetail",
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
    "Token",
    "AuthResponse",
    "Session",
    "TagBase",
    "TagInDB",
    "TrackableBase",
    "TrackableCreate",
    "TrackableUpdate",
    "TrackableInDB",
    "DayTrackableProgress",
    "DayTrackableProgressUpdate",
    "TrackableTypeWithProgress",
    "UserBase",
    "UserInDB",
]

class Msg[T](BaseModel):
    code: int | None = None
    msg: str | None = None
    data: T | None = None
