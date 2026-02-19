from pydantic import BaseModel


__all__ = [
    "Msg",
]


class Msg[T](BaseModel):
    code: int | None = None
    msg: str | None = None
    data: T | None = None
