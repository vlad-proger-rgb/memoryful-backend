import logging

from pydantic import EmailStr

from app.core.celery_app import celery
from app.core.email_templates import EMAIL_TEMPLATES
from app.core.resend_service import send_resend_email
from app.enums import EmailTemplate


logger = logging.getLogger(__name__)

@celery.task(queue="email_queue")
def send_email_task(email_type: EmailTemplate, recipients: list[EmailStr], body: dict) -> None:
    """Send an email based on the provided email_type (Enum)."""
    logger.info(f"EMAIL TASK {email_type=}, {recipients=}, {body=}")
    template_name = EMAIL_TEMPLATES.get(email_type, "default.html")

    subject = body.get("subject", "No Subject")

    response = send_resend_email(
        recipients=recipients,
        subject=subject,
        template_name=template_name,
        template_body=body,
    )

    logger.info(f"Email sent via Resend: {response}")
