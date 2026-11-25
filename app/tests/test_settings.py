import pytest
from pydantic import ValidationError

from app.core.settings import Settings


def test_trace_content_is_refused_outside_development() -> None:
    with pytest.raises(ValidationError, match="only allowed in development"):
        Settings(environment="production", ai_tracing_include_content=True)  # type: ignore[call-arg]


def test_trace_content_is_allowed_in_development() -> None:
    settings = Settings(environment="development", ai_tracing_include_content=True)  # type: ignore[call-arg]
    assert settings.ai_tracing_include_content
