import json
import logging
from typing import Annotated, AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.core.deps import get_current_user
from app.core.security import oauth2_scheme
from app.ai.services.completions import ChatAgent
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
    # Same bearer get_current_user already validated; captured here so the agent
    # loop can forward it to the MCP server for per-user data isolation.
    access_token: Annotated[str, Depends(oauth2_scheme)],
) -> Msg[CompletionResponse]:
    try:
        chat, message = await ChatAgent(db).run_completion(
            user_id,
            chat_id=data.chat_id,
            model_id=data.model_id,
            content=data.content,
            access_token=access_token,
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


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


@router.post("/stream")
async def stream_completion(
    user_id: Annotated[UUID, Depends(get_current_user())],
    data: CompletionCreate,
    access_token: Annotated[str, Depends(oauth2_scheme)],
) -> StreamingResponse:
    """Same as POST /completions, streamed as SSE: start -> token/toolCall/toolResult -> done."""

    async def event_stream() -> AsyncIterator[str]:
        # Own session, not the request-scoped one: FastAPI can close a `yield`
        # dependency before the response body finishes streaming.
        async with AsyncSessionLocal() as db:
            try:
                async for event in ChatAgent(db).stream_completion(
                    user_id,
                    chat_id=data.chat_id,
                    model_id=data.model_id,
                    content=data.content,
                    access_token=access_token,
                ):
                    yield _sse(event)
            except HTTPException as e:
                yield _sse({"type": "error", "message": e.detail})
            except Exception:
                logger.exception("Streamed completion failed for user %s", user_id)
                yield _sse({
                    "type": "error",
                    "message": "The AI provider could not complete this request. "
                               "Please try again, or pick a different model.",
                })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx: don't buffer the stream
        },
    )
