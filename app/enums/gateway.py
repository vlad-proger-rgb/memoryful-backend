from enum import StrEnum


class Gateway(StrEnum):
    google = "google"
    anthropic = "anthropic"
    vertex_maas = "vertex_maas"
    openai = "openai"
