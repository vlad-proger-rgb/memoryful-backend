from functools import cache
from typing import TYPE_CHECKING
from uuid import UUID

from app.core.settings import get_settings
from app.enums import AiUsagePurpose
from app.models import ChatModel

if TYPE_CHECKING:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.runnables import RunnableConfig
    from langsmith import Client

settings = get_settings()


@cache
def _client() -> "Client":
    from langsmith import Client

    return Client(
        api_url=settings.langsmith_endpoint,
        api_key=settings.langsmith_api_key,
        hide_inputs=True,
        hide_outputs=True,
    )


def ai_run_config(model: ChatModel, *, user_id: UUID, purpose: AiUsagePurpose) -> "RunnableConfig":
    """Callbacks and metadata given at the top of a run reach every model and tool call in it."""
    from langchain_core.tracers.langchain import LangChainTracer
    from langsmith.address import agent_address

    from app.ai.usage import UsageRecorder

    callbacks: list[BaseCallbackHandler] = []
    # Local mode runs another model under the catalog row, so its prices don't apply.
    if settings.llm_mode != "local":
        callbacks.append(UsageRecorder(model, user_id=user_id, purpose=purpose))
    if settings.ai_tracing_enabled:
        address = agent_address(settings.ai_tracing_agent_id, settings.ai_tracing_environment)
        callbacks.append(LangChainTracer(client=_client(), address=address))
    return {
        "callbacks": callbacks,
        "metadata": {"user_id": str(user_id), "purpose": purpose.value, "model": model.slug},
    }


def flush_traces() -> None:
    if not _client.cache_info().currsize:
        return
    from langchain_core.tracers.langchain import wait_for_all_tracers

    wait_for_all_tracers()
    _client().flush()
