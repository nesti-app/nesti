from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_env: str = "development"
    app_url: str = "http://localhost:8000"
    secret_key: str = ""

    database_url: str = ""

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    supabase_storage_bucket: str = "inventory-images"

    # Modern Supabase API keys (sb_publishable_... / sb_secret_...).
    # Preferred over the legacy anon / service_role JWT-based keys.
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""

    @property
    def effective_publishable_key(self) -> str:
        """Publishable (client-side) key, falling back to the legacy anon key."""
        return self.supabase_publishable_key or self.supabase_anon_key

    @property
    def effective_secret_key(self) -> str:
        """Secret (server-side) key, falling back to the legacy service_role key."""
        return self.supabase_secret_key or self.supabase_service_role_key

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
    return Settings()
