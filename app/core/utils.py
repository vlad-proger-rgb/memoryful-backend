import secrets

from app.constants import VERIFICATION_CODE_LENGTH


def generate_activation_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(VERIFICATION_CODE_LENGTH))
