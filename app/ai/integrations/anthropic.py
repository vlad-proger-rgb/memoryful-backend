import threading
import time
from functools import cached_property, partial
from typing import Any

from anthropic.lib.credentials import AccessToken, TokenCache, WorkloadIdentityCredentials
from langchain_anthropic import ChatAnthropic

from app.ai.integrations.google_identity import google_identity_token
from app.core.settings import get_settings

settings = get_settings()

# Inside the SDK's 120s refresh window, so every client re-reads the shared cache per request.
_PER_CLIENT_TOKEN_SECONDS = 60
_FEDERATION_AUDIENCE = "https://api.anthropic.com"

_shared_cache: TokenCache | None = None
_shared_cache_lock = threading.Lock()


def _federated_cache() -> TokenCache:
    global _shared_cache
    with _shared_cache_lock:
        if _shared_cache is None:
            _shared_cache = TokenCache(
                WorkloadIdentityCredentials(
                    identity_token_provider=partial(google_identity_token, _FEDERATION_AUDIENCE),
                    federation_rule_id=settings.anthropic_federation_rule_id,
                    organization_id=settings.anthropic_organization_id,
                    service_account_id=settings.anthropic_service_account_id,
                    workspace_id=settings.anthropic_workspace_id,
                )
            )
        return _shared_cache


def _federated_token(*, force_refresh: bool = False) -> AccessToken:
    """Every ChatAnthropic builds its own clients, so they all draw from one process-wide cache."""
    cache = _federated_cache()
    if force_refresh:
        cache.invalidate()
    return AccessToken(
        token=cache.get_token(), expires_at=int(time.time()) + _PER_CLIENT_TOKEN_SECONDS
    )


class _FederatedChatAnthropic(ChatAnthropic):
    @cached_property
    def _client_params(self) -> dict[str, Any]:
        params = dict(super()._client_params)
        params.pop("api_key")
        params["credentials"] = _federated_token
        return params


def build_chat_anthropic(model_name: str, **kwargs: Any) -> ChatAnthropic:
    """ChatAnthropic authenticated by Workload Identity Federation; no API key is involved."""
    # timeout/stop are aliases whose defaults mypy can't see; None is what it uses anyway.
    return _FederatedChatAnthropic(model_name=model_name, timeout=None, stop=None, **kwargs)
