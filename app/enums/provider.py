from enum import StrEnum


class Provider(StrEnum):
    openai = "openai"
    anthropic = "anthropic"
    google = "google"
    meta = "meta"
    mistral = "mistral"
    xai = "xai"
    cohere = "cohere"
    azure = "azure"
    local = "local"
    other = "other"
