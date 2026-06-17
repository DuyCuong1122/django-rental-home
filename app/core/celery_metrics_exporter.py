from __future__ import annotations

import os
import threading
import time

from prometheus_client import start_http_server
import redis

from app.core.celery_metrics import CELERY_QUEUE_LENGTH


_started = False
_poller_started = False


def start_exporter() -> None:
    global _started, _poller_started
    if _started:
        return
    if os.environ.get("CELERY_METRICS_ENABLED", "0") not in {"1", "true", "True"}:
        return
    port = int(os.environ.get("CELERY_METRICS_PORT", "8001"))
    start_http_server(port)
    _started = True

    if not _poller_started:
        _poller_started = True
        _start_queue_poller()


def _start_queue_poller() -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    queue_names = [q.strip() for q in os.environ.get("CELERY_QUEUE_NAMES", "celery").split(",") if q.strip()]
    interval_s = int(os.environ.get("CELERY_QUEUE_POLL_INTERVAL", "5"))

    def _run():
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        while True:
            for q in queue_names:
                try:
                    CELERY_QUEUE_LENGTH.labels(queue=q).set(int(client.llen(q)))
                except Exception:
                    CELERY_QUEUE_LENGTH.labels(queue=q).set(0)
            time.sleep(interval_s)

    t = threading.Thread(target=_run, daemon=True, name="celery-queue-metrics")
    t.start()


start_exporter()
