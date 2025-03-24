from pydantic import BaseModel, EmailStr


class Email(BaseModel):
    email: EmailStr

class EmailSchema(BaseModel):
    email: list[EmailStr]
    subject: str
    body: dict[str, str]

class VerifyCodeForm(Email):
    code: str
