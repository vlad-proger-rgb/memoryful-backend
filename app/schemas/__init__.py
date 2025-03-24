from pydantic import BaseModel

from .chat_model import ChatModelInDB
from .chat import ChatCreate, ChatInDB, ChatUpdate
from .city import CityInDB
from .country import CountryInDB
from .day import DayCreate, DayUpdate, DayInDB
from .email import Email, EmailSchema, VerifyCodeForm
from .learning_item import LearningItemBase, LearningItemInDB
from .learning_progress import LearningProgress
from .month import MonthBase, MonthInDB
from .security import Token, Session
from .tag import TagBase, TagInDB
from .user import UserBase, UserInDB


__all__ = [
    "Msg",
    "ChatModelInDB",
    "ChatCreate",
    "ChatInDB",
    "ChatUpdate",
    "CityInDB",
    "CountryInDB",
    "DayCreate",
    "DayUpdate",
    "DayInDB",
    "Email",
    "EmailSchema",
    "VerifyCodeForm",
    "LearningItemBase",
    "LearningItemInDB",
    "LearningProgress",
    "MonthBase",
    "MonthInDB",
    "Token",
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
