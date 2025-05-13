from uuid import UUID
import datetime as dt

from pydantic import ConfigDict, Field, field_validator
from fastapi_camelcase import CamelModel
from dateutil.parser import parse


class MonthBase(CamelModel):
    year: int = Field(dt.date.today().year)
    month: int = Field(ge=1, le=12)
    description: str | None = None
    background_image: str | None = None
    top_day_timestamp: int | None = None

    @field_validator("top_day_timestamp")
    def parse_value(cls, value: int | float | str | None) -> float | None:
        if isinstance(value, (int, float)):
            dt_ = dt.datetime.fromtimestamp(value)
            return dt_.replace(hour=0, minute=0, second=0).timestamp()
        elif isinstance(value, str):
            try:
                dt_ = parse(value)
                return dt_.replace(hour=0, minute=0, second=0).timestamp()
            except ValueError:
                pass

        if value is None:
            return None
        return float(value)

class MonthInDB(MonthBase):
    model_config = ConfigDict(from_attributes=True)
    user_id: UUID
