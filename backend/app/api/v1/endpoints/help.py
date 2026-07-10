from __future__ import annotations

from datetime import datetime
from math import ceil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_roles
from app.models.all_models import HelpComment, HelpMedia, HelpTopic, RoleCode, User
from app.services.audit_service import audit_log
from app.services.media_service import download_bytes, sha256_bytes, upload_bytes

router = APIRouter()

HELP_ADMIN_ROLES = {RoleCode.SUPER_ADMIN, RoleCode.HK_CELL_ADMIN, RoleCode.GM_OPS}
HELP_TOPIC_STATUSES = {"OPEN", "ANSWERED", "CLOSED"}
HELP_ALLOWED_MEDIA_PREFIXES = ("image/", "video/")
HELP_ALLOWED_MEDIA_TYPES = {"application/pdf"}
HELP_MAX_MEDIA_MB = max(int(settings.MAX_VIDEO_MB or 50), int(settings.MAX_PHOTO_MB or 8), 50)


class HelpTopicCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=240)
    body: str = Field(..., min_length=3, max_length=5000)


class HelpCommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class HelpAnswerCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class HelpStatusUpdate(BaseModel):
    status: str = Field(..., min_length=3, max_length=40)


def _is_help_admin(user: User) -> bool:
    return bool(user and user.role and user.role.code in HELP_ADMIN_ROLES)


def _clean_text(value: str) -> str:
    return (value or "").strip()


def _iso(value):
    return value.isoformat() if value else None


def _user_payload(user: User | None) -> dict | None:
    if not user:
        return None
    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "role": user.role.code.value if user.role else None,
    }


def _media_payload(media: HelpMedia) -> dict:
    return {
        "id": media.id,
        "topic_id": media.topic_id,
        "comment_id": media.comment_id,
        "original_file_name": media.original_file_name,
        "mime_type": media.mime_type,
        "file_size": media.file_size,
        "uploaded_by": media.uploaded_by,
        "uploaded_by_name": media.uploader.name if media.uploader else None,
        "uploaded_at": _iso(media.uploaded_at),
        "preview_url": f"/help/media/{media.id}/preview",
    }


def _topic_counts(db: Session, topic_id: int) -> dict:
    comments = db.query(HelpComment).filter(
        HelpComment.topic_id == topic_id,
        HelpComment.is_deleted.is_(False),
    ).count()
    media = db.query(HelpMedia).filter(
        HelpMedia.topic_id == topic_id,
        HelpMedia.is_deleted.is_(False),
    ).count()
    return {"comment_count": comments, "media_count": media}


def _topic_payload(db: Session, topic: HelpTopic, include_comments: bool = False) -> dict:
    counts = _topic_counts(db, topic.id)
    payload = {
        "id": topic.id,
        "title": topic.title,
        "body": topic.body,
        "status": topic.status,
        "created_by": topic.created_by,
        "created_by_user": _user_payload(topic.author),
        "answered_by": topic.answered_by,
        "answered_by_user": _user_payload(topic.answerer),
        "answered_at": _iso(topic.answered_at),
        "view_count": topic.view_count or 0,
        "is_pinned": bool(topic.is_pinned),
        "created_at": _iso(topic.created_at),
        "updated_at": _iso(topic.updated_at),
        **counts,
        "media_files": [_media_payload(media) for media in topic.media if not media.is_deleted],
    }
    if include_comments:
        comments = (
            db.query(HelpComment)
            .filter(HelpComment.topic_id == topic.id, HelpComment.is_deleted.is_(False))
            .order_by(HelpComment.is_admin_answer.desc(), HelpComment.created_at.asc(), HelpComment.id.asc())
            .all()
        )
        payload["comments"] = [_comment_payload(comment) for comment in comments]
    return payload


def _comment_payload(comment: HelpComment) -> dict:
    return {
        "id": comment.id,
        "topic_id": comment.topic_id,
        "body": comment.body,
        "created_by": comment.created_by,
        "created_by_user": _user_payload(comment.author),
        "is_admin_answer": bool(comment.is_admin_answer),
        "created_at": _iso(comment.created_at),
        "updated_at": _iso(comment.updated_at),
        "media_files": [_media_payload(media) for media in comment.media if not media.is_deleted],
    }


def _get_topic_or_404(db: Session, topic_id: int) -> HelpTopic:
    topic = db.get(HelpTopic, topic_id)
    if not topic or topic.is_deleted:
        raise HTTPException(status_code=404, detail="Help topic not found")
    return topic


def _validate_status(value: str) -> str:
    status = _clean_text(value).upper()
    if status not in HELP_TOPIC_STATUSES:
        raise HTTPException(status_code=422, detail="Status must be OPEN, ANSWERED or CLOSED")
    return status


def _validate_help_upload(file: UploadFile, data: bytes) -> None:
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(data) > HELP_MAX_MEDIA_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large. Max {HELP_MAX_MEDIA_MB} MB")

    content_type = (file.content_type or "application/octet-stream").lower()
    if content_type in HELP_ALLOWED_MEDIA_TYPES:
        return
    if any(content_type.startswith(prefix) for prefix in HELP_ALLOWED_MEDIA_PREFIXES):
        return
    raise HTTPException(status_code=400, detail="Only image, video and PDF files are allowed in Help Forum")


def _safe_filename(filename: str | None) -> str:
    name = Path(filename or "upload.bin").name.strip() or "upload.bin"
    return name.replace("/", "_").replace("\\", "_")[:180]


def _help_object_path(*, topic_id: int, comment_id: int | None, filename: str | None) -> str:
    now = datetime.utcnow()
    safe = _safe_filename(filename)
    folder = f"comment-{comment_id}" if comment_id else "topic"
    return f"help/topics/{topic_id}/{folder}/{now:%Y/%m/%d/%H%M%S%f}-{safe}"


@router.get("/topics")
def list_topics(
    search: str | None = Query(None, max_length=200),
    status: str | None = Query(None, max_length=40),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(HelpTopic).filter(HelpTopic.is_deleted.is_(False))

    if status and status.upper() != "ALL":
        query = query.filter(HelpTopic.status == _validate_status(status))

    term = _clean_text(search or "")
    if term:
        like = f"%{term}%"
        query = (
            query.outerjoin(HelpComment, HelpComment.topic_id == HelpTopic.id)
            .filter(
                or_(
                    HelpTopic.title.ilike(like),
                    HelpTopic.body.ilike(like),
                    HelpComment.body.ilike(like),
                )
            )
            .distinct()
        )

    total = query.count()
    pages = max(1, ceil(total / size)) if total else 1
    page = min(max(page, 1), pages)
    topics = (
        query.order_by(HelpTopic.is_pinned.desc(), HelpTopic.updated_at.desc(), HelpTopic.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return {
        "items": [_topic_payload(db, topic, include_comments=False) for topic in topics],
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
        "from_record": ((page - 1) * size + 1) if total else 0,
        "to_record": min(page * size, total),
        "can_answer": _is_help_admin(user),
    }


@router.post("/topics")
def create_topic(payload: HelpTopicCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    topic = HelpTopic(
        title=_clean_text(payload.title),
        body=_clean_text(payload.body),
        created_by=user.id,
        status="OPEN",
    )
    db.add(topic)
    db.flush()
    audit_log(db, actor=user, action="HELP_TOPIC_CREATED", entity_type="HelpTopic", entity_id=topic.id)
    db.commit()
    db.refresh(topic)
    return _topic_payload(db, topic, include_comments=True)


@router.get("/topics/{topic_id}")
def get_topic(topic_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    topic = _get_topic_or_404(db, topic_id)
    topic.view_count = int(topic.view_count or 0) + 1
    db.commit()
    db.refresh(topic)
    return _topic_payload(db, topic, include_comments=True)


@router.post("/topics/{topic_id}/comments")
def add_comment(topic_id: int, payload: HelpCommentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    topic = _get_topic_or_404(db, topic_id)
    comment = HelpComment(topic_id=topic.id, body=_clean_text(payload.body), created_by=user.id, is_admin_answer=False)
    topic.updated_at = datetime.utcnow()
    db.add(comment)
    db.flush()
    audit_log(db, actor=user, action="HELP_COMMENT_CREATED", entity_type="HelpComment", entity_id=comment.id, new_value={"topic_id": topic.id})
    db.commit()
    db.refresh(comment)
    return _comment_payload(comment)


@router.post("/topics/{topic_id}/answer")
def answer_topic(topic_id: int, payload: HelpAnswerCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, HELP_ADMIN_ROLES)
    topic = _get_topic_or_404(db, topic_id)
    now = datetime.utcnow()
    comment = HelpComment(topic_id=topic.id, body=_clean_text(payload.body), created_by=user.id, is_admin_answer=True)
    topic.status = "ANSWERED"
    topic.answered_by = user.id
    topic.answered_at = now
    topic.updated_at = now
    db.add(comment)
    db.flush()
    audit_log(db, actor=user, action="HELP_TOPIC_ANSWERED", entity_type="HelpTopic", entity_id=topic.id, new_value={"comment_id": comment.id})
    db.commit()
    db.refresh(comment)
    return _comment_payload(comment)


@router.patch("/topics/{topic_id}/status")
def update_topic_status(topic_id: int, payload: HelpStatusUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, HELP_ADMIN_ROLES)
    topic = _get_topic_or_404(db, topic_id)
    old_status = topic.status
    topic.status = _validate_status(payload.status)
    topic.updated_at = datetime.utcnow()
    if topic.status == "ANSWERED" and not topic.answered_by:
        topic.answered_by = user.id
        topic.answered_at = datetime.utcnow()
    db.flush()
    audit_log(db, actor=user, action="HELP_TOPIC_STATUS_UPDATED", entity_type="HelpTopic", entity_id=topic.id, old_value={"status": old_status}, new_value={"status": topic.status})
    db.commit()
    db.refresh(topic)
    return _topic_payload(db, topic, include_comments=True)


@router.post("/topics/{topic_id}/media")
async def upload_topic_media(topic_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    topic = _get_topic_or_404(db, topic_id)
    data = await file.read()
    _validate_help_upload(file, data)
    object_path = _help_object_path(topic_id=topic.id, comment_id=None, filename=file.filename)
    upload_bytes(object_path, data, file.content_type)
    media = HelpMedia(
        topic_id=topic.id,
        comment_id=None,
        object_path=object_path,
        original_file_name=_safe_filename(file.filename),
        mime_type=file.content_type or "application/octet-stream",
        file_size=len(data),
        checksum=sha256_bytes(data),
        uploaded_by=user.id,
        uploaded_at=datetime.utcnow(),
    )
    topic.updated_at = datetime.utcnow()
    db.add(media)
    db.flush()
    audit_log(db, actor=user, action="HELP_TOPIC_MEDIA_UPLOADED", entity_type="HelpMedia", entity_id=media.id, new_value={"topic_id": topic.id})
    db.commit()
    db.refresh(media)
    return _media_payload(media)


@router.post("/comments/{comment_id}/media")
async def upload_comment_media(comment_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    comment = db.get(HelpComment, comment_id)
    if not comment or comment.is_deleted:
        raise HTTPException(status_code=404, detail="Help comment not found")
    topic = _get_topic_or_404(db, comment.topic_id)
    data = await file.read()
    _validate_help_upload(file, data)
    object_path = _help_object_path(topic_id=topic.id, comment_id=comment.id, filename=file.filename)
    upload_bytes(object_path, data, file.content_type)
    media = HelpMedia(
        topic_id=topic.id,
        comment_id=comment.id,
        object_path=object_path,
        original_file_name=_safe_filename(file.filename),
        mime_type=file.content_type or "application/octet-stream",
        file_size=len(data),
        checksum=sha256_bytes(data),
        uploaded_by=user.id,
        uploaded_at=datetime.utcnow(),
    )
    topic.updated_at = datetime.utcnow()
    db.add(media)
    db.flush()
    audit_log(db, actor=user, action="HELP_COMMENT_MEDIA_UPLOADED", entity_type="HelpMedia", entity_id=media.id, new_value={"comment_id": comment.id})
    db.commit()
    db.refresh(media)
    return _media_payload(media)


@router.get("/media/{media_id}/preview")
def preview_media(media_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    media = db.get(HelpMedia, media_id)
    if not media or media.is_deleted:
        raise HTTPException(status_code=404, detail="Help media not found")
    topic = db.get(HelpTopic, media.topic_id)
    if not topic or topic.is_deleted:
        raise HTTPException(status_code=404, detail="Help topic not found")
    data = download_bytes(media.object_path)
    filename = _safe_filename(media.original_file_name)
    return Response(
        content=data,
        media_type=media.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
