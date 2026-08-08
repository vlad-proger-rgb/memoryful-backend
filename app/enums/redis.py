from enum import StrEnum


class RedisPrefix(StrEnum):
    """Prefixes for keys we build by hand — not the fastapi-cache namespaces."""

    login_code = "login_code:"
    blacklisted_token = "blacklist:"  # noqa: S105  # a key prefix, not a credential
    ai_context = "ai_context:"
    chat = "chat:"
    chat_list = "chat_list:"
