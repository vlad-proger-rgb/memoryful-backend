from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_init

from app.core.settings import get_settings

settings = get_settings()

broker_transport = None
broker_transport_options = {}
if "gcpubsub" in settings.celery_broker_url:
    broker_transport = "app.core.pubsub:Transport"
    broker_transport_options = {
        "visibility_timeout": 3600,
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
    task_ignore_result=True,
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    broker_transport=broker_transport,
)

celery.conf.beat_schedule = {
    "generate_yesterday_ai_fallback": {
        "task": "app.tasks.ai_tasks.generate_yesterday_ai_fallback",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "ai_queue"},
    },
    # Monday, two hours after the daily fallback fills in Sunday.
    "enqueue_week_digests": {
        "task": "app.tasks.ai_tasks.enqueue_week_digests",
        "schedule": crontab(hour=4, minute=0, day_of_week=1),
        "options": {"queue": "ai_queue"},
    },
}


@worker_init.connect
def _preload_ai_services(**_: object) -> None:
    # Before the pool forks, so children share these instead of each importing its own copy.
    import app.ai.integrations.vertex
    import app.ai.services.day
    import app.ai.services.week.digest  # noqa: F401
