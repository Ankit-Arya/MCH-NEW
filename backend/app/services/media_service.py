import hashlib
from datetime import datetime, timedelta
from io import BytesIO
from urllib.parse import urlparse
from minio import Minio
from minio.error import S3Error
from app.core.config import settings


def get_minio_client(
    endpoint: str | None = None,
    secure: bool | None = None,
    region: str | None = None,
) -> Minio:
    return Minio(
        endpoint or settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE if secure is None else secure,
        region=region,
    )


def ensure_bucket() -> None:
    client = get_minio_client()
    try:
        if not client.bucket_exists(settings.MINIO_BUCKET):
            client.make_bucket(settings.MINIO_BUCKET)
    except S3Error as exc:
        raise RuntimeError(f"Unable to ensure MinIO bucket: {exc}") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def upload_bytes(object_path: str, data: bytes, content_type: str | None = None) -> str:
    ensure_bucket()
    client = get_minio_client()
    client.put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=object_path,
        data=BytesIO(data),
        length=len(data),
        content_type=content_type or "application/octet-stream",
    )
    return object_path

# reads the file from MinIO using the stored object_path
def download_bytes(object_path: str) -> bytes:
    client = get_minio_client()
    response = client.get_object(settings.MINIO_BUCKET, object_path)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()

# Generate a signed MinIO URL for video
def get_external_object_url(object_path: str, expires: timedelta | None = None) -> str:
    client = get_minio_client()
    public_base = settings.MINIO_PUBLIC_BASE_URL
    if not public_base:
        return client.presigned_get_object(
            settings.MINIO_BUCKET,
            object_path,
            expires=expires or timedelta(days=7),
        )

    public_parts = urlparse(public_base)
    if not public_parts.netloc:
        return client.presigned_get_object(
            settings.MINIO_BUCKET,
            object_path,
            expires=expires or timedelta(days=7),
        )

    region = client._get_region(settings.MINIO_BUCKET)
    public_client = get_minio_client(
        endpoint=public_parts.netloc,
        secure=public_parts.scheme == "https",
        region=region,
    )
    return public_client.presigned_get_object(
        settings.MINIO_BUCKET,
        object_path,
        expires=expires or timedelta(days=7),
    )


def build_object_path(contract_id: int, station_id: int, inspection_id: int, filename: str) -> str:
    now = datetime.utcnow()
    safe = filename.replace("/", "_").replace("\\", "_")
    return f"contract-{contract_id}/station-{station_id}/{now:%Y/%m}/inspection-{inspection_id}/{safe}"
