import json
import logging
import os
import re

from openai import OpenAIError
from pydantic import ValidationError, SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.schemas.font_awesome import FAIcon
from app.models import ChatModel
from app.core.settings import (
    LLM_PROVIDER,
    OPENAI_TEMPERATURE,
    OPENAI_MODEL,
    ANTHROPIC_MODEL,
    LOCAL_LLM_BASE_URL,
    LOCAL_LLM_MODEL,
    LOCAL_LLM_API_KEY,
)


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
    """Handle OpenAI model not found errors for local/ollama providers."""
    if LLM_PROVIDER in {"local", "ollama"} and "model" in str(e).lower() and "not found" in str(e).lower():
        raise RuntimeError(
            "Local model not found in Ollama. "
            f"Requested LOCAL_LLM_MODEL='{LOCAL_LLM_MODEL}'. "
            "Run: docker exec -it ollama-dev ollama list (to see installed models) "
            f"and docker exec -it ollama-dev ollama pull {LOCAL_LLM_MODEL} (to download it)."
        ) from e
    raise


def init_chat_model_with_provider(*, db_model_name: str | None) -> BaseChatModel:
    """Initialize a chat model based on the configured LLM provider."""
    temperature = OPENAI_TEMPERATURE

    if LLM_PROVIDER in {"local", "ollama"}:
        return ChatOpenAI(
            model=LOCAL_LLM_MODEL,
            temperature=temperature,
            base_url=LOCAL_LLM_BASE_URL,
            api_key=SecretStr(LOCAL_LLM_API_KEY) if LOCAL_LLM_API_KEY else None,
        )

    if LLM_PROVIDER == "anthropic":
        return init_chat_model(ANTHROPIC_MODEL, model_provider="anthropic", temperature=temperature)

    # default: OpenAI
    model_name = db_model_name or OPENAI_MODEL
    return init_chat_model(model_name, model_provider="openai", temperature=temperature)


async def get_default_chat_model(db: AsyncSession) -> ChatModel:
    """Get the default chat model from the database."""
    preferred = await db.scalar(select(ChatModel).where(ChatModel.name == "gpt-4o-mini"))
    if preferred:
        return preferred

    model = await db.scalar(select(ChatModel).order_by(ChatModel.label.asc()).limit(1))
    if not model:
        raise RuntimeError("No chat models found")
    return model
