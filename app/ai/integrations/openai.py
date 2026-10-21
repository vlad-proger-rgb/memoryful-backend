import threading
from functools import partial
from typing import Any

from langchain_openai import ChatOpenAI
from openai.auth import WorkloadIdentityAuth

from app.ai.integrations.google_identity import google_identity_token
from app.core.settings import get_settings

settings = get_settings()

_FEDERATION_AUDIENCE = "https://api.openai.com/v1"

_shared_auth: WorkloadIdentityAuth | None = None
_shared_auth_lock = threading.Lock()


def _federated_auth() -> WorkloadIdentityAuth:
    global _shared_auth
    with _shared_auth_lock:
        if _shared_auth is None:
            _shared_auth = WorkloadIdentityAuth(
                workload_identity={
                    "identity_provider_id": settings.openai_identity_provider_id,
                    "service_account_id": settings.openai_service_account_id,
                    "provider": {
                        "token_type": "jwt",
                        "get_token": partial(google_identity_token, _FEDERATION_AUDIENCE),
                    },
                }
            )
        return _shared_auth


def _federated_token() -> str:
    """Every ChatOpenAI builds its own clients, so they all draw from one process-wide cache."""
    return _federated_auth().get_token()


def build_chat_openai(model_name: str, **kwargs: Any) -> ChatOpenAI:
    """ChatOpenAI authenticated by Workload Identity Federation; no API key is involved."""
    return ChatOpenAI(model=model_name, api_key=_federated_token, **kwargs)
