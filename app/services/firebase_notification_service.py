from __future__ import annotations

import logging
import time
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, messaging

from app.core.config import settings
from app.core.business_metrics import PUSH_SEND_LATENCY_SECONDS, PUSH_SEND_TOTAL


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_firebase_app():
    if not settings.FIREBASE_ENABLED:
        return None

    if firebase_admin._apps:
        return firebase_admin.get_app()

    try:
        cred = credentials.Certificate(settings.FCM_CREDENTIAL_PATH)
        return firebase_admin.initialize_app(cred)
    except Exception:
        logger.exception("Failed to initialize Firebase")
        return None


class FirebaseNotificationService:
    def send_multicast(self, *, tokens: list[str], title: str, body: str, data: dict[str, str]) -> dict:
        start = time.monotonic()
        app = _get_firebase_app()
        if not app:
            PUSH_SEND_TOTAL.labels(provider="fcm", result="disabled", kind=str(data.get("type") or "unknown")).inc()
            return {"success_count": 0, "failure_count": 0, "disabled": True}

        clean_tokens = [t for t in tokens if t]
        if not clean_tokens:
            PUSH_SEND_TOTAL.labels(provider="fcm", result="no_tokens", kind=str(data.get("type") or "unknown")).inc()
            return {"success_count": 0, "failure_count": 0, "disabled": False}

        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=data,
            tokens=clean_tokens,
        )

        kind = str(data.get("type") or "unknown")
        try:
            response = messaging.send_multicast(message, app=app)
        except Exception:
            PUSH_SEND_TOTAL.labels(provider="fcm", result="error", kind=kind).inc()
            raise
        finally:
            PUSH_SEND_LATENCY_SECONDS.labels(provider="fcm", kind=kind).observe(time.monotonic() - start)

        if response.failure_count:
            PUSH_SEND_TOTAL.labels(provider="fcm", result="partial_failure", kind=kind).inc()
        else:
            PUSH_SEND_TOTAL.labels(provider="fcm", result="success", kind=kind).inc()

        return {"success_count": response.success_count, "failure_count": response.failure_count}
