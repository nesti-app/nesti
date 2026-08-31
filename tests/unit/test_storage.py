from __future__ import annotations

import pytest

from app.config import get_settings
from app.media.storage import (
    S3StorageBackend,
    SupabaseStorageBackend,
    get_storage_backend,
)


def _settings(**overrides) -> dict:
    base = {
        "app_env": "development",
        "supabase_url": "https://x.supabase.co",
        "supabase_service_role_key": "svc",
        "supabase_storage_bucket": "inventory-images",
        "s3_endpoint_url": "",
        "s3_access_key_id": "",
        "s3_secret_access_key": "",
        "s3_bucket_name": "",
        "s3_region": "us-east-1",
    }
    base.update(overrides)
    return base


def test_s3_enabled_flag_requires_full_config(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "svc")
    monkeypatch.delenv("S3_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("S3_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("S3_SECRET_ACCESS_KEY", raising=False)
    settings = get_settings()
    assert settings.s3_enabled is False


def test_get_storage_backend_returns_supabase_by_default(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("S3_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("S3_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("S3_SECRET_ACCESS_KEY", raising=False)
    from app.media import storage as storage_mod

    original = storage_mod._backend
    storage_mod._backend = None
    try:
        backend = get_storage_backend()
        assert isinstance(backend, SupabaseStorageBackend)
    finally:
        storage_mod._backend = original


def test_get_storage_backend_returns_s3_when_configured(
    monkeypatch: pytest.MonkeyPatch,
):
    from app.media import storage as storage_mod

    settings = get_settings()
    monkeypatch.setattr(settings, "s3_endpoint_url", "https://x.supabase.co/storage/v1/s3")
    monkeypatch.setattr(settings, "s3_access_key_id", "ak")
    monkeypatch.setattr(settings, "s3_secret_access_key", "sk")
    monkeypatch.setattr(settings, "s3_bucket_name", "bucket")

    original = storage_mod._backend
    storage_mod._backend = None
    try:
        backend = get_storage_backend()
        assert isinstance(backend, S3StorageBackend)
    finally:
        storage_mod._backend = original


def test_storage_bucket_falls_back_to_supabase_bucket(
    monkeypatch: pytest.MonkeyPatch,
):
    settings = get_settings()
    monkeypatch.setattr(settings, "s3_bucket_name", "")
    monkeypatch.setattr(settings, "supabase_storage_bucket", "fallback-bucket")
    assert settings.storage_bucket == "fallback-bucket"


def test_storage_bucket_uses_s3_when_set(monkeypatch: pytest.MonkeyPatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "s3_bucket_name", "s3-bucket")
    monkeypatch.setattr(settings, "supabase_storage_bucket", "fallback-bucket")
    assert settings.storage_bucket == "s3-bucket"
