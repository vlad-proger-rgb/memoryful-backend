import json
import logging
import os
import re

from openai import OpenAIError
from pydantic import ValidationError, SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.schemas.font_awesome import FAIcon
from app.models import ChatModel
from app.enums.provider import Provider
from app.core.settings import (
    LLM_MODE,
    DEFAULT_TEMPERATURE,
    GCP_PROJECT_ID,
    VERTEX_LOCATION,
    LOCAL_LLM_BASE_URL,
    LOCAL_LLM_MODEL,
    LOCAL_LLM_API_KEY,
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
)

logger = logging.getLogger(__name__)


def prompts_dir() -> str:
    """Get the directory path for AI prompt files."""
    return os.path.join(os.path.dirname(__file__), "prompts")


def load_prompt(filename: str) -> str:
    """Load a prompt file from the prompts directory."""
    path = os.path.join(prompts_dir(), filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def extract_json_array(text: str) -> list[dict[str, object]]:
    """Extract a JSON array from text that may contain additional content."""
    logging.info(f"Attempting to extract JSON array from text of length {len(text)}")
    logging.debug(f"Text content: {text[:500]}...")

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            logging.info(f"Successfully parsed JSON directly, found {len(parsed)} items")
            return parsed
    except Exception as e:
        logging.debug(f"Direct JSON parsing failed: {e}")

    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        logging.error("No JSON array found in text")
        raise ValueError("LLM did not return a JSON array")

    json_str = match.group(0)
    logging.debug(f"Found JSON array: {json_str}")

    try:
        parsed = json.loads(json_str)
        if not isinstance(parsed, list):
            logging.error(f"Parsed JSON is not an array: {type(parsed)}")
            raise ValueError("LLM did not return a JSON array")
        logging.info(f"Successfully extracted and parsed JSON array with {len(parsed)} items")
        return parsed
    except Exception as e:
        logging.error(f"Failed to parse extracted JSON: {e}")
        raise ValueError(f"Failed to parse JSON array: {e}")


def sanitize_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    """Sanitize a list of items, ensuring proper icon handling."""
    logging.info(f"Sanitizing {len(items)} items")
    sanitized: list[dict[str, object]] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            logging.warning(f"Item {i+1} is not a dict: {type(item)}")
            continue

        icon = item.get("icon")
        if icon is not None:
            logging.info(f"Item {i+1} has icon: {icon} (type: {type(icon)})")
            try:
                if isinstance(icon, FAIcon):
                    item["icon"] = icon
                    logging.info(f"Item {i+1}: Icon is already valid FAIcon")
                elif isinstance(icon, dict):
                    item["icon"] = FAIcon(**icon)
                    logging.info(f"Item {i+1}: Icon converted from dict to FAIcon")
                else:
                    logging.warning(f"Item {i+1}: Invalid icon type {type(icon)}, setting to None")
                    item["icon"] = None
            except ValidationError as e:
                logging.error(f"Item {i+1}: Icon validation failed: {e}, setting to None")
                item["icon"] = None
        else:
            logging.info(f"Item {i+1}: No icon provided")

        sanitized.append(item)
    
    logging.info(f"Sanitized {len(sanitized)} items")
    return sanitized


def handle_openai_model_error(e: OpenAIError) -> None:
    """Handle 'model not found' errors when running against local Ollama."""
    if LLM_MODE == "local" and "model" in str(e).lower() and "not found" in str(e).lower():
        raise RuntimeError(
            "Local model not found in Ollama. "
            f"Requested LOCAL_LLM_MODEL='{LOCAL_LLM_MODEL}'. "
            "Run: docker exec -it ollama-dev ollama list (to see installed models) "
            f"and docker exec -it ollama-dev ollama pull {LOCAL_LLM_MODEL} (to download it)."
        ) from e
    raise


# Providers served by Vertex Model Garden through the OpenAI-compatible endpoint
# (no dedicated LangChain class exists for these). Extend as you enable more.
_VERTEX_MAAS_PROVIDERS = {Provider.xai, Provider.meta, Provider.mistral, Provider.cohere}

# Claude models that dropped temperature/top_p/top_k — passing any of them is a
# 400. Matched as prefixes so dated snapshot ids are covered too.
_ANTHROPIC_NO_SAMPLING = (
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-sonnet-5",
    "claude-fable-5",
    "claude-mythos-5",
)

# Cached ADC credentials; the access token is valid ~1h and refreshed on demand.
_gcp_credentials = None


def _vertex_access_token() -> str:
    """Mint/refresh an OAuth access token from Application Default Credentials."""
    global _gcp_credentials
    import google.auth
    from google.auth.transport.requests import Request

    if _gcp_credentials is None:
        _gcp_credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    if not _gcp_credentials.valid:
        _gcp_credentials.refresh(Request())
    return _gcp_credentials.token


def _resolve_provider(model: ChatModel) -> Provider:
    """Providers are set explicitly by the catalog sync, so this is a plain lookup."""
    try:
        return Provider(model.provider.strip().lower())
    except ValueError as e:
        raise RuntimeError(
            f"Chat model {model.name!r} has an unknown provider {model.provider!r}"
        ) from e


def _vertex_openapi_base_url(location: str) -> str:
    """Base URL for Vertex's OpenAI-compatible endpoint (Model Garden partners).

    The "global" location is served from the bare host; regional locations are
    served from a region-prefixed one.
    """
    host = (
        "aiplatform.googleapis.com"
        if location == "global"
        else f"{location}-aiplatform.googleapis.com"
    )
    return f"https://{host}/v1/projects/{GCP_PROJECT_ID}/locations/{location}/endpoints/openapi"


def build_chat_model(model: ChatModel) -> BaseChatModel:
    """Build a LangChain chat model for a specific DB `ChatModel` record.

    The gateway is chosen by `LLM_MODE`; the model id and provider come from the
    selected catalog record, so the in-app model selector actually switches models.
    """
    temperature = DEFAULT_TEMPERATURE

    # Dev: everything is served by local Ollama regardless of the catalog pick.
    if LLM_MODE == "local":
        return ChatOpenAI(
            model=LOCAL_LLM_MODEL,
            temperature=temperature,
            base_url=LOCAL_LLM_BASE_URL,
            api_key=SecretStr(LOCAL_LLM_API_KEY) if LOCAL_LLM_API_KEY else None,
        )

    provider = _resolve_provider(model)
    # Per-model region override; falls back to the global default. Some models
    # (e.g. Claude) may only have quota in a specific region, not "global".
    location = model.region or VERTEX_LOCATION

    # Gemini via the unified google-genai SDK pointed at Vertex (ADC through
    # GCP_CREDENTIALS_PATH, no API key). Imported lazily so local dev doesn't
    # need the Google libs.
    if provider is Provider.google:
        if not GCP_PROJECT_ID:
            raise RuntimeError("GCP_PROJECT_ID is required to use Vertex AI models")
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model.name,
            temperature=temperature,
            vertexai=True,
            project=GCP_PROJECT_ID,
            location=location,
        )

    # Claude through Anthropic's own API rather than Vertex Model Garden: the
    # Vertex route needs a per-model quota grant that Google declined for this
    # project. `model.name` is the direct-API id (no "@version" suffix).
    if provider is Provider.anthropic:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is required to use Claude models")
        from langchain_anthropic import ChatAnthropic

        # Newer Claude models removed the sampling parameters: sending
        # temperature to them returns a 400. Older ones still accept it.
        sampling = {} if model.name.startswith(_ANTHROPIC_NO_SAMPLING) else {"temperature": temperature}
        return ChatAnthropic(
            model=model.name,
            api_key=SecretStr(ANTHROPIC_API_KEY),
            **sampling,
        )

    # Vertex Model Garden partner models (xAI/Grok, Llama, Mistral, ...) have no
    # dedicated LangChain class — they're called via Vertex's OpenAI-compatible
    # endpoint, authenticated with an ADC access token instead of an API key.
    # `model.name` must carry the publisher prefix, e.g. "xai/grok-4.1-fast-reasoning".
    if provider in _VERTEX_MAAS_PROVIDERS:
        if not GCP_PROJECT_ID:
            raise RuntimeError("GCP_PROJECT_ID is required to use Vertex Model Garden models")
        return ChatOpenAI(
            model=model.name,
            temperature=temperature,
            base_url=_vertex_openapi_base_url(location),
            api_key=SecretStr(_vertex_access_token()),
        )

    if provider is Provider.openai:
        # Direct OpenAI API (outside GCP).
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is required to use OpenAI models")
        return ChatOpenAI(
            model=model.name,
            temperature=temperature,
            api_key=SecretStr(OPENAI_API_KEY),
        )

    raise RuntimeError(
        f"No LLM gateway configured for provider {provider!r} (model {model.name!r}) in LLM_MODE={LLM_MODE!r}"
    )


async def get_default_chat_model(db: AsyncSession) -> ChatModel:
    """Pick the fallback chat model for background jobs (insights/suggestions)."""
    base = select(ChatModel).where(ChatModel.is_active == True)  # noqa: E712

    default = await db.scalar(base.where(ChatModel.is_default == True).limit(1))  # noqa: E712
    if default:
        return default

    model = await db.scalar(base.order_by(ChatModel.sort_order.asc()).limit(1))
    if not model:
        raise RuntimeError("No active chat models found")
    return model
