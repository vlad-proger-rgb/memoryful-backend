import importlib
import logging
import threading

logger = logging.getLogger(__name__)

_MODULES = (
    "langchain.agents",
    "langchain_mcp_adapters.client",
    "langchain_google_genai",
    "app.ai.integrations.anthropic",
    "app.ai.integrations.openai",
    "app.ai.integrations.vertex",
)


def _warm_up() -> None:
    for name in _MODULES:
        try:
            importlib.import_module(name)
        except ImportError:
            logger.warning("Warm-up could not import %s", name)


def start_warm_up() -> None:
    # Off the event loop: doing this in the first request that needs it stalls every request.
    threading.Thread(target=_warm_up, name="warm-up", daemon=True).start()
