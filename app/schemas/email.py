from fastapi_camelcase import CamelModel
from pydantic import EmailStr


class Email(CamelModel):
    email: EmailStr


class EmailSchema(CamelModel):
    email: list[EmailStr]
    subject: str
    body: dict[str, str]


class VerifyCodeForm(Email):
    code: str
