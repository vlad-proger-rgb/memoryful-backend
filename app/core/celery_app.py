from celery import Celery
from celery.schedules import crontab
from app.core.settings import CELERY_BROKER_URL, CELERY_RESULT_BACKEND


celery = Celery(
    "tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)

celery.conf.beat_schedule = {
    "generate_yesterday_ai_fallback": {
        "task": "app.tasks.ai_tasks.generate_yesterday_ai_fallback",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "ai_queue"},
    }
}
