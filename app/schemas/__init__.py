from pydantic import BaseModel

from .chat_model import ChatModelInDB
from .chat import ChatCreate, ChatUpdate, ChatListItem, ChatDetail
from .city import CityInDB
from .country import CountryInDB
from .day import DayCreate, DayUpdate, DayListItem, DayDetail
from .email import Email, EmailSchema, VerifyCodeForm
from .learning_item import LearningItemCreate, LearningItemInDB
from .learning_progress import LearningProgress
from .month import MonthBase, MonthInDB
from .security import Token, AuthResponse, Session
from .tag import TagBase, TagInDB
from .user import UserBase, UserInDB


__all__ = [
    "Msg",
    "ChatModelInDB",
    "ChatCreate",
    "ChatUpdate",
    "ChatListItem",
    "ChatDetail",
    "CityInDB",
    "CountryInDB",
    "DayCreate",
    "DayUpdate",
    "DayListItem",
    "DayDetail",
    "Email",
    "EmailSchema",
    "VerifyCodeForm",
    "LearningItemCreate",
    "LearningItemInDB",
    "LearningProgress",
    "MonthBase",
    "MonthInDB",
    "Token",
    "AuthResponse",
    "Session",
    "TagBase",
    "TagInDB",
    "UserBase",
    "UserInDB",
]

class Msg[T](BaseModel):
    code: int | None = None
    msg: str | None = None
    data: T | None = None
