import random

from app.core.settings import VERIFICATION_CODE_LENGTH


def generate_activation_code() -> str:
    return ''.join(random.choices('0123456789', k=VERIFICATION_CODE_LENGTH))
