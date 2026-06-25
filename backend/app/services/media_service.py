import hashlib
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


IST = ZoneInfo("Asia/Kolkata")


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


def _media_type_value(media_type) -> str:
    return getattr(media_type, "value", str(media_type)).upper()


def _normalise_captured_at(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    return value


def _format_captured_at(value: datetime | None) -> str:
    dt = _normalise_captured_at(value)
    if dt.tzinfo is not None and dt.utcoffset() is not None:
        dt = dt.astimezone(IST)
        return dt.strftime("%d-%m-%Y %H:%M:%S IST")
    return dt.strftime("%d-%m-%Y %H:%M:%S")


def _format_coordinate(value: float | None) -> str | None:
    if value is None:
        return None
    try:
        return f"{float(value):.6f}"
    except (TypeError, ValueError):
        return None


def build_evidence_stamp_lines(
    *,
    captured_at: datetime | None,
    captured_latitude: float | None = None,
    captured_longitude: float | None = None,
    gps_accuracy: float | None = None,
) -> list[str]:
    """Return compact text that can be stamped directly on photos/videos."""

    lines = [f"Captured: {_format_captured_at(captured_at)}"]

    lat = _format_coordinate(captured_latitude)
    lon = _format_coordinate(captured_longitude)
    if lat and lon:
        gps_text = f"GPS: {lat}, {lon}"
        if gps_accuracy is not None:
            try:
                gps_text += f" | Acc: {float(gps_accuracy):.1f}m"
            except (TypeError, ValueError):
                pass
        lines.append(gps_text)

    return lines


def _load_font(size: int, bold: bool = True):
    from PIL import ImageFont

    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/DejaVuSans-Bold.ttf" if bold else "/usr/local/share/fonts/DejaVuSans.ttf",
    ]

    for path in candidates:
        if path and Path(path).exists():
            return ImageFont.truetype(path, size=size)

    return ImageFont.load_default()


def _infer_image_format(content_type: str | None, fallback: str | None = None) -> str:
    if fallback:
        return fallback.upper()
    text = (content_type or "").lower()
    if "png" in text:
        return "PNG"
    if "webp" in text:
        return "WEBP"
    return "JPEG"


def stamp_photo_bytes(
    data: bytes,
    *,
    captured_at: datetime | None,
    captured_latitude: float | None = None,
    captured_longitude: float | None = None,
    gps_accuracy: float | None = None,
    content_type: str | None = None,
) -> tuple[bytes, str | None]:
    """Permanently stamp captured date/time on image evidence.

    If Pillow cannot read the image, the original file is returned unchanged.
    This avoids breaking upload for uncommon image formats.
    """

    try:
        from PIL import Image, ImageDraw, ImageOps
    except Exception:
        return data, content_type

    try:
        image = Image.open(BytesIO(data))
        original_format = image.format
        image = ImageOps.exif_transpose(image)

        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA")

        overlay = image.convert("RGBA")
        draw = ImageDraw.Draw(overlay)

        width, height = overlay.size
        font_size = max(18, min(48, int(width * 0.035)))
        small_font_size = max(15, int(font_size * 0.78))
        font = _load_font(font_size, bold=True)
        small_font = _load_font(small_font_size, bold=False)

        lines = build_evidence_stamp_lines(
            captured_at=captured_at,
            captured_latitude=captured_latitude,
            captured_longitude=captured_longitude,
            gps_accuracy=gps_accuracy,
        )

        line_fonts = [font] + [small_font] * (len(lines) - 1)
        padding_x = max(14, int(width * 0.018))
        padding_y = max(10, int(height * 0.014))
        margin = max(14, int(width * 0.018))
        spacing = max(5, int(font_size * 0.20))

        line_boxes = [draw.textbbox((0, 0), line, font=line_font) for line, line_font in zip(lines, line_fonts)]
        text_width = max(box[2] - box[0] for box in line_boxes)
        text_height = sum(box[3] - box[1] for box in line_boxes) + spacing * (len(lines) - 1)

        box_width = min(width - 2 * margin, text_width + 2 * padding_x)
        box_height = text_height + 2 * padding_y
        x1 = margin
        y1 = max(margin, height - margin - box_height)
        x2 = x1 + box_width
        y2 = y1 + box_height

        draw.rounded_rectangle((x1, y1, x2, y2), radius=max(8, int(font_size * 0.35)), fill=(0, 0, 0, 178))

        y = y1 + padding_y
        for line, line_font, box in zip(lines, line_fonts, line_boxes):
            draw.text((x1 + padding_x, y), line, fill=(255, 255, 255, 255), font=line_font)
            y += (box[3] - box[1]) + spacing

        output_format = _infer_image_format(content_type, original_format)
        output = BytesIO()

        if output_format in {"JPEG", "JPG"}:
            stamped = overlay.convert("RGB")
            stamped.save(output, format="JPEG", quality=88, optimize=True)
            return output.getvalue(), "image/jpeg"

        if output_format == "PNG":
            overlay.save(output, format="PNG", optimize=True)
            return output.getvalue(), "image/png"

        if output_format == "WEBP":
            overlay.save(output, format="WEBP", quality=88, method=4)
            return output.getvalue(), "image/webp"

        stamped = overlay.convert("RGB")
        stamped.save(output, format="JPEG", quality=88, optimize=True)
        return output.getvalue(), "image/jpeg"
    except Exception:
        return data, content_type


def _find_ffmpeg_font() -> str | None:
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
    ]:
        if Path(path).exists():
            return path
    return None


def _escape_drawtext_path(path: str) -> str:
    return path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def stamp_video_bytes(
    data: bytes,
    *,
    captured_at: datetime | None,
    captured_latitude: float | None = None,
    captured_longitude: float | None = None,
    gps_accuracy: float | None = None,
    content_type: str | None = None,
) -> tuple[bytes, str | None]:
    """Permanently stamp captured date/time on video evidence.

    This uses ffmpeg available in the backend Docker image. If ffmpeg fails for
    any codec/container, the original video is returned unchanged so uploads do
    not fail for the inspector.
    """

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return data, content_type

    lines = build_evidence_stamp_lines(
        captured_at=captured_at,
        captured_latitude=captured_latitude,
        captured_longitude=captured_longitude,
        gps_accuracy=gps_accuracy,
    )

    with tempfile.TemporaryDirectory(prefix="mch-evidence-") as tmpdir:
        tmp = Path(tmpdir)
        input_path = tmp / "input_video"
        output_path = tmp / "output_video.mp4"
        text_path = tmp / "stamp.txt"

        input_path.write_bytes(data)
        text_path.write_text("\n".join(lines), encoding="utf-8")

        font = _find_ffmpeg_font()
        font_part = f":fontfile='{_escape_drawtext_path(font)}'" if font else ""
        text_part = _escape_drawtext_path(str(text_path))
        drawtext = (
            f"drawtext=textfile='{text_part}'{font_part}:"
            "x=24:y=h-th-24:"
            "fontsize=26:fontcolor=white:"
            "line_spacing=8:"
            "box=1:boxcolor=black@0.68:boxborderw=14"
        )

        cmd = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(input_path),
            "-vf",
            drawtext,
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "23",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        try:
            subprocess.run(cmd, check=True, timeout=180)
            processed = output_path.read_bytes()
            if processed:
                return processed, "video/mp4"
        except Exception:
            return data, content_type

    return data, content_type


def prepare_evidence_media(
    *,
    media_type,
    data: bytes,
    content_type: str | None,
    captured_at: datetime | None,
    captured_latitude: float | None = None,
    captured_longitude: float | None = None,
    gps_accuracy: float | None = None,
) -> tuple[bytes, str | None]:
    """Return upload-ready evidence bytes with visible date/time stamp.

    PHOTO evidence is stamped with Pillow.
    VIDEO evidence is stamped with ffmpeg when available.
    Other evidence types are returned unchanged.
    """

    media_type_text = _media_type_value(media_type)

    if media_type_text == "PHOTO":
        return stamp_photo_bytes(
            data,
            captured_at=captured_at,
            captured_latitude=captured_latitude,
            captured_longitude=captured_longitude,
            gps_accuracy=gps_accuracy,
            content_type=content_type,
        )

    if media_type_text == "VIDEO":
        return stamp_video_bytes(
            data,
            captured_at=captured_at,
            captured_latitude=captured_latitude,
            captured_longitude=captured_longitude,
            gps_accuracy=gps_accuracy,
            content_type=content_type,
        )

    return data, content_type
