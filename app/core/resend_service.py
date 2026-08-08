from pathlib import Path

import resend
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import EmailStr

from app.core.settings import get_settings

settings = get_settings()

resend.api_key = settings.resend_api_key

template_env = Environment(
    loader=FileSystemLoader(Path("app/templates/email")),
    # Jinja2 defaults this to off.
    autoescape=select_autoescape(["html", "xml"]),
)


def send_resend_email(
    recipients: list[EmailStr],
    subject: str,
    template_name: str,
    template_body: dict,
) -> resend.Emails.SendResponse:
    """
    Send an email using Resend with HTML template rendering.

    Args:
        recipients: List of email addresses
        subject: Email subject
        template_name: Name of the HTML template file
        template_body: Dictionary of variables to render in the template

    Returns:
        Response from Resend API
    """
    template = template_env.get_template(template_name)
    html_content = template.render(**template_body)

    params: resend.Emails.SendParams = {
        "from": f"{settings.mail_from_name} <{settings.mail_from}>",
        "to": recipients,
        "subject": subject,
        "html": html_content,
    }

    return resend.Emails.send(params)
