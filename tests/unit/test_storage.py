from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.config import get_settings
from app.media.storage import S3StorageBackend, get_storage_backend


@pytest.fixture(autouse=True)
def _reset_backend_cache() -> Iterator[None]:
    from app.media import storage as storage_mod

    original = storage_mod._backend
    storage_mod._backend = None
    yield
    storage_mod._backend = original


def test_s3_enabled_requires_credentials(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("S3_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("S3_SECRET_ACCESS_KEY", raising=False)
    settings = get_settings()
    assert settings.s3_enabled is False


def test_get_storage_backend_raises_without_config(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("S3_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("S3_SECRET_ACCESS_KEY", raising=False)
    with pytest.raises(RuntimeError, match="AWS_ACCESS_KEY_ID"):
        get_storage_backend()


def test_get_storage_backend_returns_s3_when_configured(
    monkeypatch: pytest.MonkeyPatch,
):
    settings = get_settings()
    monkeypatch.setattr(settings, "aws_access_key_id", "ak")
    monkeypatch.setattr(settings, "aws_secret_access_key", "sk")

    backend = get_storage_backend()
    assert isinstance(backend, S3StorageBackend)


def test_storage_bucket_uses_s3_bucket(monkeypatch: pytest.MonkeyPatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "s3_bucket_name", "s3-bucket")
    assert settings.storage_bucket == "s3-bucket"
