import logging

from celery import Celery
from app.core.config import settings
from app.core import celery_metrics
from app.core import celery_metrics_exporter

celery_app = Celery(
    "rental_house",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    include=["app.tasks.notification_tasks"],
)

# Example background task
@celery_app.task
def dummy_task():
    logging.getLogger(__name__).info("Celery is running properly.")
