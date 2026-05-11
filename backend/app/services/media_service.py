import hashlib
from datetime import datetime
from io import BytesIO
from minio import Minio
from minio.error import S3Error
from app.core.config import settings


def get_minio_client() -> Minio:
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
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


def build_object_path(contract_id: int, station_id: int, inspection_id: int, filename: str) -> str:
    now = datetime.utcnow()
    safe = filename.replace("/", "_").replace("\\", "_")
    return f"contract-{contract_id}/station-{station_id}/{now:%Y/%m}/inspection-{inspection_id}/{safe}"
