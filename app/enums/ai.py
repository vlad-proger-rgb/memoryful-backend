from enum import StrEnum


class AnalysisPurpose(StrEnum):
    """What a background AI job is generating. Each one picks its own chat model,
    so a cheap model can write daily insights while a stronger one reads the week."""

    day = "day"
    week = "week"


class AiUsagePurpose(StrEnum):
    chat = "chat"
    day = "day"
    week = "week"


class AiRunName(StrEnum):
    """A raw run is the plain retry after structured output failed."""

    chat = "chat"
    chat_plain = "chat (plain)"
    day_insights = "day insights"
    day_insights_raw = "day insights (raw)"
    day_suggestions = "day suggestions"
    day_suggestions_raw = "day suggestions (raw)"
    week_digest = "week digest"
    week_digest_raw = "week digest (raw)"


class AiRunTrigger(StrEnum):
    user = "user"
    scheduled = "scheduled"
