from fastapi import APIRouter

from . import chats, completions, chat_models

router = APIRouter(prefix="/ai")
router.include_router(chats.router)
router.include_router(completions.router)
router.include_router(chat_models.router)
