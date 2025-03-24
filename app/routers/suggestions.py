from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.schemas import (
    Msg,
    ChatInDB,
)
from app.core.database import get_db
from app.models import Suggestion
from app.core.deps import get_current_user


router = APIRouter(
    prefix="/suggestions",
    tags=["Suggestions"],
)
