import logging
import random
import os

from google.cloud import secretmanager

logger = logging.getLogger(__name__)


def generate_activation_code() -> str:
    from app.core.settings import VERIFICATION_CODE_LENGTH
    return ''.join(random.choices('0123456789', k=VERIFICATION_CODE_LENGTH))


def get_secret(secret_name: str) -> str:
    """Fetch secret from GCP Secret Manager"""
    from app.core.settings import GCP_PROJECT_ID, USE_SECRET_MANAGER

    if not USE_SECRET_MANAGER:
        return os.getenv(secret_name) or ""

    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT_ID}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(name=name)
        return response.payload.data.decode('UTF-8')

    except Exception as e:
        logger.error(f"Failed to fetch secret {secret_name} from Secret Manager: {e}")
        # Fallback to environment variable
        return os.getenv(secret_name) or ""
