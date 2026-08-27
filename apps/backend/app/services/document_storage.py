from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from app.settings import settings


SIGNED_URL_TTL_SECONDS = 300


@runtime_checkable
class DocumentStorage(Protocol):
    """Provider-neutral storage operations used by the document pipeline."""

    def ensure_bucket(self) -> None:
        ...

    def upload(self, storage_key: str, contents: bytes, *, content_type: str) -> None:
        ...

    def download(self, storage_key: str) -> bytes:
        ...

    def create_download_url(self, storage_key: str, expires_in: int) -> str:
        ...


class SupabaseDocumentStorage:
    def __init__(self, client: Any, *, bucket: str):
        self._client = client
        self._bucket = bucket

    def ensure_bucket(self) -> None:
        try:
            self._client.storage.get_bucket(self._bucket)
        except Exception:
            self._client.storage.create_bucket(self._bucket)

    def upload(self, storage_key: str, contents: bytes, *, content_type: str) -> None:
        self._client.storage.from_(self._bucket).upload(
            storage_key,
            contents,
            {"content-type": content_type, "upsert": "true"},
        )

    def download(self, storage_key: str) -> bytes:
        return self._client.storage.from_(self._bucket).download(storage_key)

    def create_download_url(self, storage_key: str, expires_in: int) -> str:
        response = self._client.storage.from_(self._bucket).create_signed_url(
            storage_key,
            expires_in,
        )
        if not isinstance(response, Mapping):
            raise RuntimeError("Supabase returned an invalid signed PDF URL response")
        signed_url = response.get("signedURL") or response.get("signedUrl")
        if not isinstance(signed_url, str) or not signed_url:
            raise RuntimeError("Supabase did not return a signed PDF URL")
        return signed_url


class S3DocumentStorage:
    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str | None = None,
        public_endpoint_url: str | None = None,
        region_name: str = "us-east-1",
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        client: Any | None = None,
        presign_client: Any | None = None,
    ):
        self._bucket = bucket
        self._client = client or _create_s3_client(
            endpoint_url=endpoint_url,
            region_name=region_name,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
        )
        self._presign_client = presign_client
        if self._presign_client is None:
            self._presign_client = (
                _create_s3_client(
                    endpoint_url=public_endpoint_url,
                    region_name=region_name,
                    access_key_id=access_key_id,
                    secret_access_key=secret_access_key,
                )
                if public_endpoint_url and public_endpoint_url != endpoint_url
                else self._client
            )

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except self._client.exceptions.ClientError:
            self._client.create_bucket(Bucket=self._bucket)

    def upload(self, storage_key: str, contents: bytes, *, content_type: str) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Key=storage_key,
            Body=contents,
            ContentType=content_type,
        )

    def download(self, storage_key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=storage_key)
        return response["Body"].read()

    def create_download_url(self, storage_key: str, expires_in: int) -> str:
        return self._presign_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": storage_key},
            ExpiresIn=expires_in,
        )


def create_document_storage() -> DocumentStorage:
    if settings.storage_backend == "s3":
        return S3DocumentStorage(
            bucket=settings.storage_bucket,
            endpoint_url=settings.s3_endpoint_url,
            public_endpoint_url=settings.s3_public_endpoint_url,
            region_name=settings.s3_region,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
        )

    return SupabaseDocumentStorage(
        _create_supabase_client(),
        bucket=settings.storage_bucket,
    )


def _create_supabase_client() -> Any:
    from supabase import create_client

    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _create_s3_client(
    *,
    endpoint_url: str | None,
    region_name: str,
    access_key_id: str | None,
    secret_access_key: str | None,
) -> Any:
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=region_name,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        config=Config(s3={"addressing_style": "path"}),
    )
