from celery import Celery
from app.core.config import settings

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
)

# Example background task
@celery_app.task
def dummy_task():
    print("Celery is running properly.")
