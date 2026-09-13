from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.utils import get_chosen_chat_model, get_default_chat_model
from app.constants import CACHE_TTL_USER_DATA
from app.core.cache import cached, clear_cache
from app.core.database import get_db
from app.core.deps import get_current_user
from app.enums import AnalysisPurpose, CacheNamespace
from app.models import AiModelPreference, ChatModel
from app.schemas import ChatModelRef, Msg, PurposeModel, PurposeModelIn

router = APIRouter(
    prefix="/model-preferences",
    tags=["AI Model Preferences"],
)


Preferences = dict[AnalysisPurpose, PurposeModel]


async def _preferences(db: AsyncSession, user_id: UUID) -> Preferences:
    default = await get_default_chat_model(db)
    purposes: Preferences = {}
    for purpose in AnalysisPurpose:
        chosen = await get_chosen_chat_model(db, user_id=user_id, purpose=purpose)
        purposes[purpose] = PurposeModel(
            model=ChatModelRef.model_validate(chosen or default),
            is_default=chosen is None,
        )
    return purposes


@router.get("/me", response_model=Msg[Preferences])
@cached(expire=CACHE_TTL_USER_DATA, namespace=CacheNamespace.ai_model_preferences)
async def get_my_model_preferences(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
) -> Msg[Preferences]:
    data = await _preferences(db, user_id)
    return Msg(code=200, msg="AI model preferences retrieved", data=data)


@router.put("/me/{purpose}", response_model=Msg[Preferences])
async def set_my_model_preference(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    purpose: AnalysisPurpose,
    body: PurposeModelIn,
) -> Msg[Preferences]:
    if body.model_id is None:
        await db.execute(
            delete(AiModelPreference).where(
                AiModelPreference.user_id == user_id,
                AiModelPreference.purpose == purpose.value,
            )
        )
    else:
        offered = await db.scalar(
            select(ChatModel.id).where(ChatModel.id == body.model_id, ChatModel.is_active == True)
        )
        if offered is None:
            raise HTTPException(404, "Chat Model not found")
        await db.merge(
            AiModelPreference(user_id=user_id, purpose=purpose.value, model_id=body.model_id)
        )

    await db.commit()
    await clear_cache(CacheNamespace.ai_model_preferences, user_id)

    data = await _preferences(db, user_id)
    return Msg(code=200, msg="AI model preference updated", data=data)
