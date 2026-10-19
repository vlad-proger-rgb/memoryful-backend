import threading
from typing import Any

from app.core.settings import get_settings

settings = get_settings()

_credentials_by_audience: dict[str, Any] = {}
_credentials_lock = threading.Lock()


def _credentials_for(audience: str) -> Any:
    import google.auth
    from google.auth import impersonated_credentials

    with _credentials_lock:
        if audience not in _credentials_by_audience:
            source, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            target = impersonated_credentials.Credentials(
                source_credentials=source,
                target_principal=settings.gcp_ai_service_account,
                target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            # Federation rules match on the email claim, which Google omits unless asked.
            _credentials_by_audience[audience] = impersonated_credentials.IDTokenCredentials(
                target, target_audience=audience, include_email=True
            )
        return _credentials_by_audience[audience]


def google_identity_token(audience: str) -> str:
    """OIDC token for GCP_AI_SERVICE_ACCOUNT, minted by impersonating it from ADC."""
    from google.auth.transport.requests import Request

    credentials = _credentials_for(audience)
    if not credentials.valid:
        credentials.refresh(Request())
    token = credentials.token
    if not token:
        raise RuntimeError(f"Google returned no identity token for audience {audience!r}")
    return str(token)
