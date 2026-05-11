from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "mch_inspection_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.timezone = "Asia/Kolkata"
celery_app.conf.beat_schedule = {
    "daily-health-task": {
        "task": "app.workers.tasks.daily_health_task",
        "schedule": 60 * 60 * 24,
    }
}
