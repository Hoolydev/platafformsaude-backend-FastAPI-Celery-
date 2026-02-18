"""
Celery App — configuração central
"""

from celery import Celery
from app.config import settings

celery_app = Celery(
    "saude_workers",
    broker=settings.CELERY_BROKER_URL or "redis://localhost:6379/0",
    backend=settings.CELERY_BROKER_URL or "redis://localhost:6379/0",
    include=[
        "app.workers.message_processor",
        "app.workers.reminders",
        "app.workers.lead_recovery",
        "app.workers.tasks",
    ],
)

celery_app.conf.update(
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Beat schedule importado do scheduler
from app.workers.scheduler import BEAT_SCHEDULE  # noqa: E402
celery_app.conf.beat_schedule = BEAT_SCHEDULE
