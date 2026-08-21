import os
from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from app.core.secrets import SecretManagerError, apply_credentials_path, fetch_secrets


class SettingsError(RuntimeError):
    """Configuration is missing or malformed."""


# The credentials the app cannot run without. Every one is required, and in
# production every one comes from GCP Secret Manager under its upper-cased name.
REQUIRED_SECRETS = frozenset(
    {
        "postgres_user",
        "postgres_password",
        "postgres_host",
        "redis_host",
        "redis_password",
        "access_secret_key",
        "refresh_secret_key",
        "resend_api_key",
        "mail_from",
        "s3_access_key_id",
        "s3_secret_access_key",
        "openai_api_key",
        "anthropic_api_key",
    }
)

_LOCAL_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


class SecretManagerSource(PydanticBaseSettingsSource):
    """Resolves REQUIRED_SECRETS, ranked below the environment so `.env.prod` wins."""

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        raise NotImplementedError  # unused: __call__ resolves every field in one batch

    def __call__(self) -> dict[str, Any]:
        if os.getenv("USE_SECRET_MANAGER", "").strip().lower() != "true":
            return {}

        project_id = os.getenv("GCP_PROJECT_ID", "").strip()
        if not project_id:
            raise SecretManagerError("USE_SECRET_MANAGER is on but GCP_PROJECT_ID is unset")

        if unknown := REQUIRED_SECRETS - set(self.settings_cls.model_fields):
            raise SecretManagerError(
                f"REQUIRED_SECRETS names fields that do not exist: {sorted(unknown)}"
            )

        apply_credentials_path()
        wanted = sorted(f.upper() for f in REQUIRED_SECRETS if not os.getenv(f.upper()))
        secrets = fetch_secrets(wanted, project_id=project_id)
        return {name.lower(): value for name, value in secrets.items()}


class Settings(BaseSettings):
    """Every environment-derived value, resolved once by `get_settings`.

    Deliberately no `env_file`: compose supplies the environment, and the repo's own
    `.env` is host tooling holding a production connection string.
    """

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # GCP
    gcp_project_id: str = ""
    use_secret_manager: bool = False
    gcp_credentials_path: str = ""
    gcp_pubsub_project_id: str = ""

    # Environment
    environment: Literal["development", "production"] = "development"
    seed_db_on_empty: bool = False

    # Postgres
    postgres_user: str = Field(min_length=1)
    postgres_password: str = Field(min_length=1)
    postgres_host: str = Field(min_length=1)
    postgres_port: int = 5432
    postgres_db: str = "memoryful"
    postgres_sslmode: str = "require"
    sql_echo: bool = False

    # Tokens
    access_secret_key: str = Field(min_length=1)
    refresh_secret_key: str = Field(min_length=1)
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7

    # Redis
    redis_host: str = Field(min_length=1)
    redis_port: int = 6379
    redis_password: str = Field(min_length=1)
    redis_db: int = 0
    redis_ssl: bool = False

    # Resend email
    resend_api_key: str = Field(min_length=1)
    mail_from: str = Field(min_length=1)
    mail_from_name: str | None = None

    # Auth
    trusted_emails_raw: str = Field("", validation_alias="TRUSTED_EMAILS")

    # Google OAuth
    google_client_ids_raw: str = Field("", validation_alias="GOOGLE_CLIENT_IDS")

    # CORS
    allowed_origins_raw: str = Field("", validation_alias="ALLOWED_ORIGINS")
    allow_credentials_raw: bool | None = Field(None, validation_alias="ALLOW_CREDENTIALS")
    allowed_methods_raw: str = Field("*", validation_alias="ALLOWED_METHODS")
    allowed_headers_raw: str = Field("*", validation_alias="ALLOWED_HEADERS")

    # S3 / GCS
    s3_endpoint_url: str = "https://storage.googleapis.com"
    s3_access_key_id: str = Field(min_length=1)
    s3_secret_access_key: str = Field(min_length=1)
    s3_region: str = "europe-central2"
    s3_bucket: str = "memoryful"
    s3_public_base_url: str = "https://storage.googleapis.com"

    # Cache
    cache_enabled: bool = True

    # LLM
    #
    # llm_mode decides the *gateway*, not the model. The model itself is chosen
    # per-request from the `chat_models` DB catalog (see app/ai/utils.build_chat_model):
    #   - "local"  -> every request is served by the local Ollama container.
    #                 The catalog selection is ignored; local_llm_model is used.
    #   - "vertex" -> route by the selected model's `provider`, all through GCP
    #                 Vertex AI using ADC (no API keys).
    llm_mode: Literal["local", "vertex"] = "local"

    # Vertex AI region. "global" routes across regions and is the widest-availability
    # option — partner models (Claude, Grok) are often only offered there.
    vertex_location: str = "global"

    # MCP server (streamable-HTTP) the in-app agent loads its tools from. FastMCP's
    # canonical path is /mcp with NO trailing slash — /mcp/ 307-redirects to it,
    # doubling every round-trip.
    mcp_server_url: str = "http://mcp:3001/mcp"

    default_temperature: float = Field(0.4, validation_alias="LLM_TEMPERATURE")

    # Local dev (Ollama, OpenAI-compatible endpoint).
    local_llm_base_url: str = "http://ollama:11434/v1"
    local_llm_model: str = "llama3.1"
    local_llm_api_key: str = "local"

    # Direct provider APIs (used for provider=openai / provider=anthropic models).
    openai_api_key: str = Field(min_length=1)
    anthropic_api_key: str = Field(min_length=1)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            SecretManagerSource(settings_cls),
        )

    @field_validator("llm_mode", mode="before")
    @classmethod
    def _normalize_llm_mode(cls, value: Any) -> Any:
        return value.strip().lower() if isinstance(value, str) else value

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def main_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        protocol = "rediss" if self.redis_ssl else "redis"
        auth = f"default:{self.redis_password}@"
        url = f"{protocol}://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"{url}?ssl_cert_reqs=CERT_REQUIRED" if self.redis_ssl else url

    @property
    def celery_broker_url(self) -> str:
        return f"gcpubsub://projects/{self.gcp_pubsub_project_id or self.gcp_project_id}"

    @property
    def celery_result_backend(self) -> str:
        return self.redis_url

    @property
    def trusted_emails(self) -> frozenset[str]:
        """These addresses skip login verification, so the set stays empty outside development."""
        if not self.is_development:
            return frozenset()
        return frozenset(e.strip().lower() for e in self.trusted_emails_raw.split(",") if e.strip())

    def is_trusted_email(self, email: str) -> bool:
        """Normalizes the same way the set is built, so the two cannot drift apart."""
        return email.strip().lower() in self.trusted_emails

    @property
    def google_client_ids(self) -> list[str]:
        return [c.strip() for c in self.google_client_ids_raw.split(",") if c.strip()]

    @property
    def allowed_origins(self) -> list[str]:
        origins = [o.strip() for o in self.allowed_origins_raw.split(",") if o.strip()]
        if not origins and self.is_development:
            return list(_LOCAL_CORS_ORIGINS)
        return origins

    @property
    def allow_credentials(self) -> bool:
        if self.allow_credentials_raw is None:
            return self.is_development
        return self.allow_credentials_raw

    @property
    def allowed_methods(self) -> list[str]:
        return self.allowed_methods_raw.split(",")

    @property
    def allowed_headers(self) -> list[str]:
        return self.allowed_headers_raw.split(",")


@lru_cache
def get_settings() -> Settings:
    """Resolve settings once per process. Raises on anything missing or malformed."""
    apply_credentials_path()
    try:
        # mypy reads the required fields as constructor arguments; the sources supply them.
        return Settings()  # type: ignore[call-arg]
    except ValidationError as e:
        # Re-raised without the original: pydantic renders every input value into its
        # message, which would put every API key in the logs.
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])} ({error['msg']})"
            for error in e.errors()
        )
        raise SettingsError(f"Invalid configuration: {problems}") from None
