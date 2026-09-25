from __future__ import annotations

from collections.abc import Iterator

import pytest
from botocore.exceptions import ClientError

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
    settings = get_settings()
    monkeypatch.setattr(settings, "aws_access_key_id", "")
    monkeypatch.setattr(settings, "aws_secret_access_key", "")
    assert settings.s3_enabled is False


def test_get_storage_backend_raises_without_config(monkeypatch: pytest.MonkeyPatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "aws_access_key_id", "")
    monkeypatch.setattr(settings, "aws_secret_access_key", "")
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


class _FakeClient:
    def __init__(self, *, missing: bool = False) -> None:
        self._missing = missing
        self.created = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def head_bucket(self, **_: object) -> None:
        if self._missing:
            raise ClientError(
                {"Error": {"Code": "404", "Message": "Not Found"}},
                "HeadBucket",
            )
        return None

    async def create_bucket(self, **_: object) -> None:
        self.created = True


class _FakeBackend:
    """Minimal stand-in whose ``_client()`` yields a fake S3 client."""

    def __init__(self, *, missing: bool = False) -> None:
        self.client = _FakeClient(missing=missing)
        self.bucket = "test-bucket"

    async def _client(self):
        return self.client


async def test_ensure_bucket_creates_when_missing(monkeypatch: pytest.MonkeyPatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "s3_bucket_name", "test-bucket")
    backend = S3StorageBackend(settings)
    fake = _FakeBackend(missing=True)
    monkeypatch.setattr(backend, "_client", fake._client)

    await backend.ensure_bucket()

    assert fake.client.created is True


async def test_ensure_bucket_noop_when_exists(monkeypatch: pytest.MonkeyPatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "s3_bucket_name", "test-bucket")
    backend = S3StorageBackend(settings)
    fake = _FakeBackend(missing=False)
    monkeypatch.setattr(backend, "_client", fake._client)

    await backend.ensure_bucket()

    assert fake.client.created is False
