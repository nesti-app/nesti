from __future__ import annotations

import os
from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def get_settings() -> Settings:
    env_file = os.environ.get("SETTINGS_FILE", "").strip()
    if env_file:
        return Settings(_env_file=env_file)
    return Settings()
