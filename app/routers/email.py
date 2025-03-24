from fastapi import APIRouter, HTTPException

from app.tasks.email_tasks import send_email_task
from app.schemas import Msg, EmailSchema
from app.core.enums import EmailTemplate

router = APIRouter(
    prefix="/email-sender",
    tags=["Email Sender"],
)

@router.post("/send-email", response_model=Msg[None])
async def send_email(data: EmailSchema) -> Msg[None]:
    try:
        email_type = EmailTemplate(data.body.get("type"))
    except ValueError:
        raise HTTPException(400, "Invalid email type")

    send_email_task.delay(email_type, data.email, data.body)
    return Msg(code=200, msg="Email is being sent in the background")
