from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services.firebase_notification_service import FirebaseNotificationService


logger = logging.getLogger(__name__)


async def _send_push_notification_async(*, receiver_id: UUID, title: str, body: str, data: dict[str, str]) -> None:
    async with AsyncSessionLocal() as db:
        stmt = (
            select(User)
            .where(User.id == receiver_id, User.is_deleted == False)
        )
        res = await db.execute(stmt)
        user = res.scalars().first()
        if not user or not getattr(user, "fcm_token", None):
            logger.info("No FCM token for user_id=%s", receiver_id)
            return

        service = FirebaseNotificationService()
        logger.info("Sending push notification user_id=%s", receiver_id)
        result = service.send_multicast(tokens=[user.fcm_token], title=title, body=body, data=data)
        logger.info(
            "FCM send result user_id=%s success=%s failure=%s",
            receiver_id,
            result.get("success_count"),
            result.get("failure_count"),
        )


@celery_app.task(name="send_push_notification")
def send_push_notification(receiver_id: str, title: str, body: str, data: dict | None = None) -> None:
    try:
        rid = UUID(str(receiver_id))
    except Exception:
        logger.warning("Invalid receiver_id=%s", receiver_id)
        return

    payload = {str(k): str(v) for k, v in (data or {}).items()}
    asyncio.run(_send_push_notification_async(receiver_id=rid, title=title, body=body, data=payload))


@celery_app.task(name="send_chat_notification")
def send_chat_notification(receiver_id: str, title: str, body: str, data: dict | None = None) -> None:
    return send_push_notification(receiver_id=receiver_id, title=title, body=body, data=data)
