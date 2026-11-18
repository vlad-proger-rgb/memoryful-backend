import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING, assert_never
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.enums import AnalysisPurpose, Gateway
from app.models import AiModelPreference, ChatModel

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

settings = get_settings()


logger = logging.getLogger(__name__)


def prompts_dir() -> Path:
    return Path(__file__).parent / "prompts"


def load_prompt(filename: str) -> str:
    return (prompts_dir() / filename).read_text(encoding="utf-8").strip()


# Cached ADC credentials; the access token is valid ~1h and refreshed on demand.
_gcp_credentials = None
_gcp_credentials_lock = threading.Lock()


def _vertex_access_token() -> str:
    """Blocks on Google, so it is passed as a key provider that the async client runs off-loop."""
    global _gcp_credentials
    import google.auth
    from google.auth.transport.requests import Request

    with _gcp_credentials_lock:
        if _gcp_credentials is None:
            _gcp_credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        if not _gcp_credentials.valid:
            _gcp_credentials.refresh(Request())
        token = _gcp_credentials.token
    if token is None:
        raise RuntimeError("GCP credentials carry no access token after refresh")
    return str(token)


def _resolve_gateway(model: ChatModel) -> Gateway:
    try:
        return Gateway(model.gateway or "")
    except ValueError as e:
        raise RuntimeError(
            f"Chat model {model.name!r} has no known gateway: {model.gateway!r}"
        ) from e


def _vertex_openapi_base_url(location: str) -> str:
    host = (
        "aiplatform.googleapis.com"
        if location == "global"
        else f"{location}-aiplatform.googleapis.com"
    )
    project_id = settings.gcp_project_id
    return f"https://{host}/v1/projects/{project_id}/locations/{location}/endpoints/openapi"


def build_chat_model(model: ChatModel) -> "BaseChatModel":
    """The catalog record picks the gateway; `LLM_MODE=local` overrides it for every model."""
    temperature = settings.default_temperature

    if settings.llm_mode == "local":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.local_llm_model,
            temperature=temperature,
            base_url=settings.local_llm_base_url,
            api_key=SecretStr(settings.local_llm_api_key) if settings.local_llm_api_key else None,
        )

    gateway = _resolve_gateway(model)

    # Imported lazily so local dev doesn't need the Google libs.
    if gateway is Gateway.google:
        if not settings.gcp_project_id:
            raise RuntimeError("GCP_PROJECT_ID is required to use Vertex AI models")
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model.name,
            temperature=temperature,
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.vertex_location,
        )

    # Claude through Anthropic's own API rather than Vertex Model Garden: the
    # Vertex route needs a per-model quota grant that Google declined for this
    # project. `model.name` is the direct-API id (no "@version" suffix).
    if gateway is Gateway.anthropic:
        from app.ai.integrations.anthropic import build_chat_anthropic

        if model.no_sampling:
            return build_chat_anthropic(model.name)
        return build_chat_anthropic(model.name, temperature=temperature)

    if gateway is Gateway.vertex_maas:
        if not settings.gcp_project_id:
            raise RuntimeError("GCP_PROJECT_ID is required to use Vertex Model Garden models")
        from app.ai.integrations.vertex import VertexMaaSChatOpenAI

        return VertexMaaSChatOpenAI(
            model=model.name,
            temperature=temperature,
            base_url=_vertex_openapi_base_url(settings.vertex_location),
            api_key=_vertex_access_token,
        )

    if gateway is Gateway.openai:
        from app.ai.integrations.openai import build_chat_openai

        return build_chat_openai(model.name, temperature=temperature)

    assert_never(gateway)


async def get_default_chat_model(db: AsyncSession) -> ChatModel:
    base = select(ChatModel).where(ChatModel.is_active == True)

    default = await db.scalar(base.where(ChatModel.is_default == True).limit(1))
    if default:
        return default

    model = await db.scalar(base.order_by(ChatModel.sort_order.asc()).limit(1))
    if not model:
        raise RuntimeError("No active chat models found")
    return model


async def get_chosen_chat_model(
    db: AsyncSession, *, user_id: UUID, purpose: AnalysisPurpose
) -> ChatModel | None:
    chosen: ChatModel | None = await db.scalar(
        select(ChatModel)
        .join(AiModelPreference, AiModelPreference.model_id == ChatModel.id)
        .where(
            AiModelPreference.user_id == user_id,
            AiModelPreference.purpose == purpose.value,
            ChatModel.is_active == True,
        )
    )
    return chosen


async def get_chat_model_for(
    db: AsyncSession, *, user_id: UUID, purpose: AnalysisPurpose
) -> ChatModel:
    chosen = await get_chosen_chat_model(db, user_id=user_id, purpose=purpose)
    return chosen or await get_default_chat_model(db)
