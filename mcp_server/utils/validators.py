"""Common validation utilities for MCP server tools."""


def validate_non_empty_string(value: str | None, field_name: str) -> None:
    """Validate that a string parameter is not empty or just whitespace."""
    if value is not None:
        if not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string if provided")


def validate_non_negative_int(value: int, field_name: str) -> None:
    """Validate that an integer parameter is non-negative."""
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def validate_month_number(month_number: int) -> None:
    """Validate that month number is between 1 and 12."""
    if month_number < 1 or month_number > 12:
        raise ValueError("month_number must be between 1 and 12")
