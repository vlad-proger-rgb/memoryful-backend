from enum import StrEnum


class CacheNamespace(StrEnum):
    """Namespaces shared by `@cached` reads and `clear_cache` writes."""

    users = "users"
    days_list = "days_list"
    days_detail = "days_detail"
    months = "months"
    tags = "tags"
    trackables = "trackables"
    trackable_types = "trackable_types"
    workspaces = "workspaces"
    insights = "insights"
    suggestions = "suggestions"
    chat_models = "chat_models"
    cities = "cities"
    countries = "countries"
