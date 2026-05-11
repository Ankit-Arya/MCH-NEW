from app.workers.celery_app import celery_app


@celery_app.task
def daily_health_task() -> str:
    return "worker-ok"


@celery_app.task
def validate_media_task(media_id: int) -> dict:
    # Extend this with ffprobe duration validation and image metadata extraction.
    return {"media_id": media_id, "status": "VALIDATED"}
