import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.ai.services import chat as chat_service
from app.schemas import Msg, CompletionCreate, CompletionResponse

logger = logging.getLogger(__name__)

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
    except HTTPException:
        raise
    except Exception as e:
        # Any provider failure (quota, auth, timeout, bad model id) lands here.
        # The real cause goes to the logs; the client gets a safe, actionable
        # message rather than a 500 and a stack trace.
        logger.exception("Completion failed for user %s", user_id)
        raise HTTPException(
            502,
            "The AI provider could not complete this request. "
            "Please try again, or pick a different model.",
        ) from e

    return Msg(
        code=200,
        msg="Completion generated",
        data=CompletionResponse(chat_id=chat.id, title=chat.title, message=message),
    )
