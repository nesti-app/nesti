from __future__ import annotations

import asyncio
from typing import Any, Protocol

from botocore.exceptions import ClientError

from app.config import Settings, get_settings


class StorageBackend(Protocol):
    """Async object-storage interface shared by the image-related operations."""

    async def upload(self, path: str, data: bytes, content_type: str) -> None: ...

    async def download(self, path: str) -> bytes: ...

    async def delete(self, paths: list[str]) -> None: ...

    async def signed_url(self, path: str, expires_in: int = 3600) -> str: ...


class S3StorageBackend:
    """S3-compatible backend backed by aiobotocore (fully async).

    Used to talk to Supabase Storage's S3 endpoint (or any S3 provider).
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def _bucket(self) -> str:
        return self._settings.storage_bucket

    def _client_kwargs(self) -> dict[str, Any]:
        from botocore.config import Config

        return {
            "endpoint_url": self._settings.s3_endpoint_url,
            "aws_access_key_id": self._settings.s3_access_key_id,
            "aws_secret_access_key": self._settings.s3_secret_access_key,
            "region_name": self._settings.s3_region,
            # Supabase's S3-compatible API only supports path-style addressing.
            # With an HTTPS endpoint (no explicit port) boto3 defaults to
            # virtual-hosted-style, which resolves to the wrong host and makes
            # every request fail.
            "config": Config(s3={"addressing_style": "path"}),
        }

    async def _client(self) -> Any:
        import aiobotocore

        session = aiobotocore.get_session()
        return session.create_client("s3", **self._client_kwargs())

    async def upload(self, path: str, data: bytes, content_type: str) -> None:
        async with await self._client() as client:
            await client.put_object(
                Bucket=self._bucket,
                Key=path,
                Body=data,
                ContentType=content_type,
            )

    async def download(self, path: str) -> bytes:
        async with await self._client() as client:
            response = await client.get_object(Bucket=self._bucket, Key=path)
            body = response["Body"]
            data: bytes = await body.read()
            return data

    async def delete(self, paths: list[str]) -> None:
        if not paths:
            return
        async with await self._client() as client:
            kwargs: dict[str, Any] = {
                "Bucket": self._bucket,
                "Delete": {"Objects": [{"Key": p} for p in paths]},
            }
            if len(paths) == 1:
                # delete_objects requires at least the Quiet flag or one object;
                # a single empty Delete is not sent. Be explicit with Quiet.
                kwargs["Delete"]["Quiet"] = True
            try:
                await client.delete_objects(**kwargs)
            except ClientError:
                # Some providers reject EmptyObjectList for a single object.
                # Fall back to a plain delete_object call.
                for p in paths:
                    await client.delete_object(Bucket=self._bucket, Key=p)

    async def signed_url(self, path: str, expires_in: int = 3600) -> str:
        async with await self._client() as client:
            return await asyncio.to_thread(
                client.generate_presigned_url,
                "get_object",
                Params={"Bucket": self._bucket, "Key": path},
                ExpiresIn=expires_in,
            )


class SupabaseStorageBackend:
    """Fallback backend wrapping the legacy synchronous supabase-py client."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _client(self) -> Any:
        from supabase import create_client

        return create_client(
            self._settings.supabase_url, self._settings.effective_secret_key
        ).storage.from_(self._settings.supabase_storage_bucket)

    async def upload(self, path: str, data: bytes, content_type: str) -> None:
        def _do() -> None:
            self._client().upload(
                path, data, file_options={"content-type": content_type}
            )

        await asyncio.to_thread(_do)

    async def download(self, path: str) -> bytes:
        return await asyncio.to_thread(self._client().download, path)

    async def delete(self, paths: list[str]) -> None:
        if not paths:
            return
        await asyncio.to_thread(self._client().remove, paths)

    async def signed_url(self, path: str, expires_in: int = 3600) -> str:
        result = await asyncio.to_thread(
            self._client().create_signed_url, path, expires_in=expires_in
        )
        return (result.get("signedUrl") if isinstance(result, dict) else result) or ""


_backend: StorageBackend | None = None


def get_storage_backend(settings: Settings | None = None) -> StorageBackend:
    """Return a lazily-initialized storage backend based on configuration."""
    global _backend
    if _backend is None:
        settings = settings or get_settings()
        if settings.s3_enabled:
            _backend = S3StorageBackend(settings)
        else:
            _backend = SupabaseStorageBackend(settings)
    return _backend
