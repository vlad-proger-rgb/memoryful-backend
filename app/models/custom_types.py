import logging
from typing import Type, Optional

from sqlalchemy import TypeDecorator, JSON
from sqlalchemy.engine import Dialect
from pydantic import BaseModel, ValidationError


logger = logging.getLogger(__name__)

class PydanticType[T: BaseModel](TypeDecorator):
    impl = JSON
    cache_ok = True

    def __init__(self, pydantic_model: Type[T], *args: object, **kwargs: object) -> None:
        self.pydantic_model = pydantic_model
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value: T | dict | None, dialect: Dialect) -> T | dict | None:
        if value is None:
            return None

        if isinstance(value, self.pydantic_model):
            return value.model_dump()
        elif isinstance(value, dict):
            try:
                validated = self.pydantic_model(**value)
                return validated.model_dump()
            except ValidationError as e:
                logger.warning(f"Invalid {self.pydantic_model.__name__} data: {e}")
                raise ValueError(f"Invalid {self.pydantic_model.__name__} format")

        return value

    def process_result_value(self, value: Optional[dict], dialect: Dialect) -> Optional[T]:
        if value is None:
            return None

        try:
            return self.pydantic_model(**value)
        except ValidationError:
            logger.warning(f"Corrupted {self.pydantic_model.__name__} in database: {value}")
            return None
