from __future__ import annotations

import time
from typing import Any

from celery.signals import task_failure, task_postrun, task_prerun, task_retry
from prometheus_client import Counter, Gauge, Histogram


_task_start: dict[str, float] = {}

CELERY_TASK_RUNTIME_SECONDS = Histogram(
    "celery_task_runtime_seconds",
    "Celery task runtime in seconds.",
    labelnames=("task",),
)
CELERY_TASK_SUCCESS_TOTAL = Counter(
    "celery_task_success_total",
    "Total number of successful Celery tasks.",
    labelnames=("task",),
)
CELERY_TASK_FAILURE_TOTAL = Counter(
    "celery_task_failure_total",
    "Total number of failed Celery tasks.",
    labelnames=("task", "exception_type"),
)
CELERY_TASK_RETRY_TOTAL = Counter(
    "celery_task_retry_total",
    "Total number of retried Celery tasks.",
    labelnames=("task",),
)
CELERY_TASK_INFLIGHT = Gauge(
    "celery_task_inflight",
    "Number of Celery tasks currently executing.",
    labelnames=("task",),
)
CELERY_QUEUE_LENGTH = Gauge(
    "celery_queue_length",
    "Broker queue length (best-effort for Redis broker).",
    labelnames=("queue",),
)


def _task_name(sender: Any | None) -> str:
    if not sender:
        return "unknown"
    return getattr(sender, "name", None) or sender.__class__.__name__


@task_prerun.connect
def _on_task_prerun(task_id: str, task, *args, **kwargs):
    name = _task_name(task)
    _task_start[task_id] = time.monotonic()
    CELERY_TASK_INFLIGHT.labels(task=name).inc()


@task_postrun.connect
def _on_task_postrun(task_id: str, task, state: str | None = None, *args, **kwargs):
    name = _task_name(task)
    start = _task_start.pop(task_id, None)
    if start is not None:
        CELERY_TASK_RUNTIME_SECONDS.labels(task=name).observe(time.monotonic() - start)

    CELERY_TASK_INFLIGHT.labels(task=name).dec()

    if state == "SUCCESS":
        CELERY_TASK_SUCCESS_TOTAL.labels(task=name).inc()


@task_failure.connect
def _on_task_failure(task_id: str, sender, exception, *args, **kwargs):
    name = _task_name(sender)
    exc_type = exception.__class__.__name__ if exception else "Exception"
    CELERY_TASK_FAILURE_TOTAL.labels(task=name, exception_type=exc_type).inc()


@task_retry.connect
def _on_task_retry(request, reason, *args, **kwargs):
    name = _task_name(getattr(request, "task", None))
    CELERY_TASK_RETRY_TOTAL.labels(task=name).inc()
