"""Chat system prompt: a base persona (`chat_system.md`) plus Jinja2 blocks under
`prompts/context/`, each contributing only when it has data.
"""

import asyncio
import logging
from uuid import UUID

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import UserProfile
from app.ai.utils import load_prompt, prompts_dir
from app.constants import CACHE_TTL_USER_DATA
from app.core.config import redis
from app.enums import Prompt, RedisPrefix
from app.models import User

logger = logging.getLogger(__name__)

# trim/lstrip keep the template's control lines from leaking blank lines into the block.
_env = Environment(
    loader=FileSystemLoader(prompts_dir()),
    autoescape=False,  # noqa: S701  # prompts are not HTML; escaping would corrupt them
    trim_blocks=True,
    lstrip_blocks=True,
    undefined=StrictUndefined,
)


def render_user_profile(profile: UserProfile) -> str:
    return (
        _env.get_template("context/user_profile.md.j2")
        .render(name=profile.first_name, age=profile.age, bio=profile.bio)
        .strip()
    )


async def get_user_profile(db: AsyncSession, user_id: UUID) -> UserProfile:
    """Cached minimal profile for prompt context. Invalidated on `PUT /auth/me`."""
    key = f"{RedisPrefix.ai_context}{user_id}"
    cached = await redis.get(key)
    if cached:
        return UserProfile.model_validate_json(cached)

    user = await db.get(User, user_id)
    profile = UserProfile(
        first_name=user.first_name if user else None,
        age=user.age if user else None,
        bio=user.bio if user else None,
    )
    await redis.set(key, profile.model_dump_json(), ex=CACHE_TTL_USER_DATA)
    return profile


class ChatContextBuilder:
    """Assembles the chat system prompt from the base persona plus optional blocks."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def system_prompt(self, user_id: UUID) -> str:
        base = load_prompt(Prompt.chat_system)
        # Blocks load concurrently; each returns "" when it has nothing to add.
        blocks = await asyncio.gather(
            self._user_profile(user_id),
        )
        return "\n\n".join([base, *(b for b in blocks if b)])

    async def _user_profile(self, user_id: UUID) -> str:
        profile = await get_user_profile(self.db, user_id)
        if profile.is_empty:
            return ""
        return render_user_profile(profile)
