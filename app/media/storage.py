from __future__ import annotations

import logging
from typing import Any, Protocol, cast

from botocore.exceptions import ClientError

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class StorageBackend(Protocol):
    """Async object-storage interface shared by the image-related operations."""

    async def upload(self, path: str, data: bytes, content_type: str) -> None: ...

    async def download(self, path: str) -> bytes: ...

    async def delete(self, paths: list[str]) -> None: ...

    async def signed_url(self, path: str, expires_in: int = 3600) -> str: ...

    async def ensure_bucket(self) -> None: ...


class S3StorageBackend:
    """S3-compatible backend backed by aiobotocore (fully async).

    Works with any S3 provider: Supabase Storage, rustfs, MinIO, classic AWS...
    Providers differ only by endpoint URL and path-style addressing preference.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def _bucket(self) -> str:
        return self._settings.storage_bucket

    def _client_kwargs(self) -> dict[str, Any]:
        from botocore.config import Config

        addressing_style: str | None = "path" if self._settings.s3_force_path_style else None
        kwargs: dict[str, Any] = {
            "aws_access_key_id": self._settings.aws_access_key_id,
            "aws_secret_access_key": self._settings.aws_secret_access_key,
            "region_name": self._settings.aws_default_region,
        }
        if self._settings.aws_endpoint_url:
            kwargs["endpoint_url"] = self._settings.aws_endpoint_url
        if addressing_style:
            kwargs["config"] = Config(s3={"addressing_style": addressing_style})
        return kwargs

    async def _client(self) -> Any:
        from aiobotocore.session import get_session

        return get_session().create_client("s3", **self._client_kwargs())

    async def ensure_bucket(self) -> None:
        """Create the bucket if it does not exist (best-effort)."""
        try:
            async with await self._client() as client:
                await client.head_bucket(Bucket=self._bucket)
        except ClientError as exc:
            error_code = exc.response["Error"].get("Code")
            if error_code in ("404", "NoSuchBucket"):
                async with await self._client() as client:
                    await client.create_bucket(Bucket=self._bucket)
                logger.info("Created S3 bucket: %s", self._bucket)
            else:
                raise

    async def upload(self, path: str, data: bytes, content_type: str) -> None:
        try:
            async with await self._client() as client:
                await client.put_object(
                    Bucket=self._bucket,
                    Key=path,
                    Body=data,
                    ContentType=content_type,
                )
        except Exception:
            logger.exception(
                "S3 upload failed (endpoint=%s bucket=%s key=%s)",
                self._settings.aws_endpoint_url,
                self._bucket,
                path,
            )
            raise

    async def download(self, path: str) -> bytes:
        try:
            async with await self._client() as client:
                response = await client.get_object(Bucket=self._bucket, Key=path)
                body = response["Body"]
                data: bytes = await body.read()
                return data
        except Exception:
            logger.exception(
                "S3 download failed (endpoint=%s bucket=%s key=%s)",
                self._settings.aws_endpoint_url,
                self._bucket,
                path,
            )
            raise

    async def delete(self, paths: list[str]) -> None:
        if not paths:
            return
        try:
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
        except Exception:
            logger.exception(
                "S3 delete failed (endpoint=%s bucket=%s keys=%s)",
                self._settings.aws_endpoint_url,
                self._bucket,
                paths,
            )
            raise

    async def signed_url(self, path: str, expires_in: int = 3600) -> str:
        try:
            async with await self._client() as client:
                # aiobotocore's generate_presigned_url is async (returns a coroutine).
                url = await client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self._bucket, "Key": path},
                    ExpiresIn=expires_in,
                )
                return cast(str, url)
        except Exception:
            logger.exception(
                "S3 signed_url failed (endpoint=%s bucket=%s key=%s)",
                self._settings.aws_endpoint_url,
                self._bucket,
                path,
            )
            raise


_backend: StorageBackend | None = None


def get_storage_backend(settings: Settings | None = None) -> StorageBackend:
    """Return a lazily-initialized S3 backend based on configuration.

    Raises RuntimeError with a clear message when S3 is not configured
    (credentials are required; the App must not run without storage).
    """
    global _backend
    if _backend is None:
        settings = settings or get_settings()
        if not settings.s3_enabled:
            raise RuntimeError(
                "Object storage is not configured: AWS_ACCESS_KEY_ID and "
                "AWS_SECRET_ACCESS_KEY must be set."
            )
        _backend = S3StorageBackend(settings)
    return _backend
