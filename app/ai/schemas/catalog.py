from collections import Counter
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.enums import Gateway, Provider


class ChatModelSpec(BaseModel):
    """Prices in USD per 1M tokens, limits in tokens."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]*$")
    label: str
    provider: Provider
    gateway: Gateway
    provider_model: str
    no_sampling: bool = False
    input_price: float | None = None
    cached_input_price: float | None = None
    output_price: float | None = None
    context_limit: int | None = None
    output_limit: int | None = None


class ChatModelCatalog(BaseModel):
    """The list order is the selector order, and the first model is the default."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    models: list[ChatModelSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_unique_slugs(self) -> Self:
        slug_counts = Counter(model.slug for model in self.models)
        duplicates = [slug for slug, count in slug_counts.items() if count > 1]
        if duplicates:
            raise ValueError(f"duplicate slugs: {duplicates}")
        return self
