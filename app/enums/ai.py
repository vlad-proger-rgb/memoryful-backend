from enum import StrEnum


class AnalysisPurpose(StrEnum):
    """What a background AI job is generating. Each one picks its own chat model,
    so a cheap model can write daily insights while a stronger one reads the week."""

    day = "day"
    week = "week"
