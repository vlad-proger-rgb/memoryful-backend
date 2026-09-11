from typing import NoReturn

from openai import OpenAIError

from app.core.settings import get_settings

settings = get_settings()


def handle_openai_model_error(e: OpenAIError) -> NoReturn:
    """Re-raise, naming the pull command when local Ollama has no such model."""
    if settings.llm_mode == "local" and "model" in str(e).lower() and "not found" in str(e).lower():
        raise RuntimeError(
            "Local model not found in Ollama. "
            f"Requested LOCAL_LLM_MODEL='{settings.local_llm_model}'. "
            "Run: docker exec -it memoryful-ollama-local ollama list (to see installed "
            "models) and docker exec -it memoryful-ollama-local ollama pull "
            f"{settings.local_llm_model} (to download it)."
        ) from e
    raise
