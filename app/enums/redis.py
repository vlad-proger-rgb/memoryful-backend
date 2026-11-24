from enum import StrEnum


class RedisPrefix(StrEnum):
    """Prefixes for keys we build by hand — not the fastapi-cache namespaces."""

    login_code = "login_code:"
    google_nonce = "google_nonce:"
    revoked_session = "revoked_session:"
    ai_context = "ai_context:"
    chat = "chat:"
    chat_list = "chat_list:"
