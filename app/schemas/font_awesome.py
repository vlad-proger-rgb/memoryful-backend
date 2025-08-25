from pydantic import BaseModel
from app.enums import IconStyle

class FAIcon(BaseModel):
    name: str
    style: IconStyle = IconStyle.fas
