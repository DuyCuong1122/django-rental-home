from __future__ import annotations

import asyncio
from uuid import UUID

from ninja.errors import HttpError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user import UserRepository
from app.services.firebase_notification_service import FirebaseNotificationService


class UserService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def save_fcm_token(self, *, user_id: UUID, token: str, platform: str) -> None:
        user = await self.repo.update_fcm_token(user_id=str(user_id), token=token, platform=platform)
        if not user:
            raise HttpError(404, "User not found")

    async def send_push_test(
        self,
        *,
        sender_id: UUID,
        receiver_id: UUID | None,
        title: str,
        body: str,
        data: dict[str, str],
    ) -> dict:
        rid = receiver_id or sender_id
        user = await self.repo.get_by_id(str(rid))
        if not user:
            raise HttpError(404, "User not found")

        token = getattr(user, "fcm_token", None)
        if not token:
            return {"receiver_id": rid, "has_token": False, "disabled": False, "success_count": 0, "failure_count": 0}

        payload = {str(k): str(v) for k, v in (data or {}).items()}
        service = FirebaseNotificationService()
        result = await asyncio.to_thread(service.send_multicast, tokens=[token], title=title, body=body, data=payload)

        return {
            "receiver_id": rid,
            "has_token": True,
            "disabled": bool(result.get("disabled")),
            "success_count": int(result.get("success_count", 0)),
            "failure_count": int(result.get("failure_count", 0)),
        }
