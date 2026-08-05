import logging

from pydantic import BaseModel, ValidationError
from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.engine import Dialect

logger = logging.getLogger(__name__)


class PydanticType[T: BaseModel](TypeDecorator):
    impl = JSON
    cache_ok = True

    def __init__(self, pydantic_model: type[T], *args: object, **kwargs: object) -> None:
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
                raise ValueError(f"Invalid {self.pydantic_model.__name__} format") from e

        return value

    def process_result_value(self, value: dict | None, dialect: Dialect) -> T | None:
        if value is None:
            return None

        try:
            return self.pydantic_model(**value)
        except ValidationError:
            logger.warning(f"Corrupted {self.pydantic_model.__name__} in database: {value}")
            return None
