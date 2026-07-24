from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.ai.services import chat as chat_service
from app.schemas import Msg, CompletionCreate, CompletionResponse

router = APIRouter(
    prefix="/completions",
    tags=["AI Completions"],
)


@router.post("/", response_model=Msg[CompletionResponse])
async def create_completion(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[UUID, Depends(get_current_user())],
    data: CompletionCreate,
) -> Msg[CompletionResponse]:
    try:
        chat, message = await chat_service.run_completion(
            db,
            user_id,
            chat_id=data.chat_id,
            model_id=data.model_id,
            content=data.content,
        )
    except OpenAIError as e:
        raise HTTPException(502, f"AI provider error: {e}") from e

    return Msg(
        code=200,
        msg="Completion generated",
        data=CompletionResponse(chat_id=chat.id, title=chat.title, message=message),
    )
