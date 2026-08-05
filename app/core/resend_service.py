from pathlib import Path

import resend
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import EmailStr

from app.core.settings import MAIL_FROM, MAIL_FROM_NAME, RESEND_API_KEY

resend.api_key = RESEND_API_KEY

template_env = Environment(
    loader=FileSystemLoader(Path("app/templates/email")),
    # Jinja2 defaults to off. These render HTML mail from user-supplied values.
    autoescape=select_autoescape(["html", "xml"]),
)


def send_resend_email(
    recipients: list[EmailStr],
    subject: str,
    template_name: str,
    template_body: dict,
) -> dict:
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

    params = {
        "from": f"{MAIL_FROM_NAME} <{MAIL_FROM}>",
        "to": recipients,
        "subject": subject,
        "html": html_content,
    }

    response = resend.Emails.send(params)
    return response
