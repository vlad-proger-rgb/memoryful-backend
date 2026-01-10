from pydantic import BaseModel, field_validator, Field
from app.enums import IconStyle

class FAIcon(BaseModel):
    name: str = Field(description="Font Awesome icon name")
    style: IconStyle = Field(default=IconStyle.fas, description="Font Awesome icon style (short name, .e.g. fas, fab, etc.)")

    @field_validator("style", mode="before")
    @classmethod
    def _normalize_style(cls, v: object) -> object:
        if isinstance(v, str):
            normalized = v.strip().lower()
            alias_map: dict[str, str] = {
                "solid": "fas",
                "regular": "far",
                "brands": "fab",
                "brand": "fab",
                "light": "fal",
                "duotone": "fad",
                "thin": "fat",
            }
            return alias_map.get(normalized, normalized)
        return v
