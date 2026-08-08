"""Chat prompt-context assembly.

The chat system prompt is composed from a base persona (`chat_system.md`) plus
optional context blocks, each a Jinja2 template under `prompts/context/` that
contributes only when it has data. Add a block by writing a template and a small
loader method on `ChatContextBuilder`.
"""

import asyncio
import logging
from uuid import UUID

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.utils import load_prompt, prompts_dir
from app.constants import CACHE_TTL_USER_DATA
from app.core.config import redis
from app.enums import RedisPrefix
from app.models import User

logger = logging.getLogger(__name__)

# autoescape off: prompts are plain text/markdown, not HTML. trim/lstrip keep the
# template's control lines from leaking blank lines into the rendered block.
_env = Environment(
    loader=FileSystemLoader(prompts_dir()),
    autoescape=False,  # noqa: S701  # prompts are not HTML; escaping would corrupt them
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_block(template: str, /, **context: object) -> str:
    """Render a Jinja2 prompt block and strip surrounding whitespace."""
    return _env.get_template(template).render(**context).strip()


class UserProfile(BaseModel):
    """Minimal user facts used to personalize chat. Cached, so kept small."""

    first_name: str | None = None
    last_name: str | None = None
    age: int | None = None
    bio: str | None = None

    @property
    def name(self) -> str:
        return " ".join(p for p in (self.first_name, self.last_name) if p)

    @property
    def is_empty(self) -> bool:
        return not (self.first_name or self.last_name or self.age or self.bio)


async def get_user_profile(db: AsyncSession, user_id: UUID) -> UserProfile:
    """Cached minimal profile for prompt context. Invalidated on `PUT /auth/me`."""
    key = f"{RedisPrefix.ai_context}{user_id}"
    cached = await redis.get(key)
    if cached:
        return UserProfile.model_validate_json(cached)

    user = await db.get(User, user_id)
    profile = UserProfile(
        first_name=user.first_name if user else None,
        last_name=user.last_name if user else None,
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
        base = load_prompt("chat_system.md")
        # Blocks load concurrently; each returns "" when it has nothing to add.
        blocks = await asyncio.gather(
            self._user_profile(user_id),
            # future: self._recent_days(user_id), self._active_focus(user_id), ...
        )
        return "\n\n".join([base, *(b for b in blocks if b)])

    async def _user_profile(self, user_id: UUID) -> str:
        profile = await get_user_profile(self.db, user_id)
        if profile.is_empty:
            return ""
        return render_block(
            "context/user_profile.md.j2",
            name=profile.name,
            age=profile.age,
            bio=profile.bio,
        )
