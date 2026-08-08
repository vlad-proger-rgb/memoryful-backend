from celery import Celery
from celery.schedules import crontab

from app.core.settings import get_settings

settings = get_settings()

# Configure broker transport options for PubSub
broker_transport_options = {}
if "gcpubsub" in settings.celery_broker_url:
    broker_transport_options = {
        "visibility_timeout": 3600,  # 1 hour
        "dead_letter_queue": "celery-dlq",
        "max_retries": 3,
    }

celery = Celery(
    "tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
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
