import asyncio

from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import EmailStr

from app.core.config import conf
from app.core.celery_app import celery
from app.core.email_templates import EMAIL_TEMPLATES
from app.enums import EmailTemplate


@celery.task(queue="email_queue")
def send_email_task(email_type: EmailTemplate, recipients: list[EmailStr], body: dict) -> None:
    """Send an email based on the provided email_type (Enum)."""
    print(f"EMAIL TASK {email_type=}, {recipients=}, {body=}")
    template_name = EMAIL_TEMPLATES.get(email_type, "default.html")  # Fallback

    message = MessageSchema(
        subject=body.get("subject", "No Subject"),
        recipients=recipients,
        template_body=body,
        subtype=MessageType.html,
    )

    fm = FastMail(conf)
    asyncio.run(fm.send_message(message, template_name=template_name))
