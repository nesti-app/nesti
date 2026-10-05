from __future__ import annotations

import logging
import os
import secrets
from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Session cookies are HS256 JWTs, so SECRET_KEY is the only thing separating
# "signed by this server" from "signed by anyone". Anything short or obviously
# a placeholder is treated as unusable.
MIN_SECRET_KEY_LENGTH = 32

WEAK_SECRET_KEYS = frozenset(
    {
        "secret",
        "secretkey",
        "secret_key",
        "changeme",
        "change-me",
        "change_me",
        "password",
        "supersecret",
        "super-secret",
        "insecure",
        "nesti",
        "dev",
        "development",
        "test",
        "testing",
        "placeholder",
        "example",
        "your-secret-key",
    }
)


def _is_repeated_pattern(key: str, max_unit: int = 16) -> bool:
    """Detect keys that are one short chunk repeated, e.g. ``changemechangeme…``.

    Padding a placeholder out to the minimum length must not make it acceptable.
    A real random token is never periodic over such a short unit.
    """
    for size in range(1, max_unit + 1):
        if len(key) < size * 2 or len(key) % size:
            continue
        unit = key[:size]
        if unit * (len(key) // size) == key:
            return True
    return False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    app_url: str = "http://localhost:8000"
    secret_key: str = ""

    database_url: str = ""

    # Bootstrap admin: first-start upsert from env when using local auth.
    admin_email: str = ""
    admin_password: str = ""

    # Anti-bruteforce on login (per-account lockout + optional IP throttle).
    login_max_attempts: int = 5
    login_lockout_seconds: int = 900
    ip_throttle_per_minute: int = 20

    # S3-compatible object storage (any provider: Supabase Storage, rustfs,
    # MinIO, classic AWS, ...). Standard AWS env-var names are canonical;
    # the legacy S3_* spellings are accepted as aliases via validation_alias.
    aws_access_key_id: str = Field(
        default="",
        validation_alias=AliasChoices("AWS_ACCESS_KEY_ID", "S3_ACCESS_KEY_ID"),
    )
    aws_secret_access_key: str = Field(
        default="",
        validation_alias=AliasChoices("AWS_SECRET_ACCESS_KEY", "S3_SECRET_ACCESS_KEY"),
    )
    aws_default_region: str = Field(
        default="us-east-1",
        validation_alias=AliasChoices("AWS_DEFAULT_REGION", "S3_REGION"),
    )
    aws_endpoint_url: str = Field(
        default="",
        validation_alias=AliasChoices("AWS_ENDPOINT_URL", "S3_ENDPOINT_URL"),
    )
    s3_bucket_name: str = Field(default="", validation_alias="S3_BUCKET_NAME")
    s3_force_path_style: bool = Field(default=True, validation_alias="S3_FORCE_PATH_STYLE")

    @property
    def s3_enabled(self) -> bool:
        return bool(self.aws_access_key_id and self.aws_secret_access_key)

    @property
    def storage_bucket(self) -> str:
        return self.s3_bucket_name

    max_upload_size: int = 10_485_760
    image_max_dimension: int = 2400
    thumbnail_max_dimension: int = 256
    label_dpi: int = 203

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def has_usable_secret_key(self) -> bool:
        """True when SECRET_KEY is long enough and not a known placeholder."""
        key = self.secret_key.strip()
        if len(key) < MIN_SECRET_KEY_LENGTH:
            return False
        if key.lower() in WEAK_SECRET_KEYS:
            return False
        return not _is_repeated_pattern(key)

    def resolve_secret_key(self) -> str:
        """Return a signing key that is safe to use for session tokens.

        In production an unusable SECRET_KEY is a hard error: the app must
        refuse to start rather than sign sessions with a predictable secret.
        Elsewhere a random per-process key is generated so local development
        still works, with a warning — that key dies with the process, so
        sessions do not survive a restart.
        """
        if self.has_usable_secret_key:
            return self.secret_key

        if self.is_production:
            raise RuntimeError(
                "SECRET_KEY is missing, too short, or a placeholder. "
                f"Set SECRET_KEY to a random value of at least {MIN_SECRET_KEY_LENGTH} "
                'characters, e.g. python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )

        logger.warning(
            "SECRET_KEY is missing, too short, or a placeholder; generating a temporary "
            "random key. All sessions will be invalidated on restart. Set SECRET_KEY in "
            "your .env to keep sessions across restarts."
        )
        return secrets.token_urlsafe(64)


@lru_cache
def get_settings() -> Settings:
    env_file = os.environ.get("SETTINGS_FILE", "").strip()
    settings = Settings(_env_file=env_file) if env_file else Settings()
    settings.secret_key = settings.resolve_secret_key()
    return settings
