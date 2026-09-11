from pydantic import BaseModel

from app.schemas.font_awesome import FAIcon


class AIItem(BaseModel):
    description: str
    icon: FAIcon | None = None
    content: str


class AIItemList(BaseModel):
    items: list[AIItem]
