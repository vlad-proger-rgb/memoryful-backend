"""GCP Secret Manager access, used only while settings are being loaded."""

import logging
import os
from collections.abc import Iterable

from google.api_core.exceptions import NotFound
from google.cloud import secretmanager

logger = logging.getLogger(__name__)


class SecretManagerError(RuntimeError):
    """Secret Manager was enabled but could not be read."""


def apply_credentials_path() -> None:
    """Google's clients read ADC from this variable, so it must be set before any of them exist."""
    if path := os.getenv("GCP_CREDENTIALS_PATH"):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path


def fetch_secrets(names: Iterable[str], *, project_id: str) -> dict[str, str]:
    """Read the named secrets' latest versions over a single shared channel.

    A secret that does not exist is skipped, since several are optional and pydantic
    already enforces the required ones. Every other failure raises: degrading to a
    blank credential is the behaviour this replaces.
    """
    names = list(names)
    if not names:
        return {}

    resolved: dict[str, str] = {}
    with secretmanager.SecretManagerServiceClient() as client:
        for name in names:
            try:
                response = client.access_secret_version(
                    name=f"projects/{project_id}/secrets/{name}/versions/latest"
                )
            except NotFound:
                logger.warning("Secret %s is not present in Secret Manager", name)
                continue
            except Exception as e:
                raise SecretManagerError(f"Could not read secret {name}: {e}") from e

            resolved[name] = response.payload.data.decode("utf-8")

    logger.info("Loaded %d/%d secrets from Secret Manager", len(resolved), len(names))
    return resolved
