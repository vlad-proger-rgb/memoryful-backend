from celery import Celery
from celery.schedules import crontab
from app.core.settings import CELERY_BROKER_URL, CELERY_RESULT_BACKEND


# Configure broker transport options for PubSub
broker_transport_options = {}
if "gcpubsub" in CELERY_BROKER_URL:
    broker_transport_options = {
        "visibility_timeout": 3600,  # 1 hour
        "dead_letter_queue": "celery-dlq",
        "max_retries": 3,
    }

celery = Celery(
    "tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks"],
    broker_transport_options=broker_transport_options,
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
