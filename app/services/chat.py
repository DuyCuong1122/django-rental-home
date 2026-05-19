from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from ninja.errors import HttpError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.repositories.chat import ChatRepository
from app.schemas.chat import (
    ChatInboxItem,
    ChatInboxResponse,
    ChatLastMessageBrief,
    ChatMessageItem,
    ChatMessagesResponse,
    ChatParticipantBrief,
    ChatRoomBrief,
    ChatRoomDetailResponse,
    CreateChatRoomResponse,
    PresignChatImageResponse,
)
from app.selectors.chat import decode_cursor, encode_cursor
from apps.upload.services import S3UploadService


class ChatService:
    def __init__(self, db: AsyncSession):
        self.repo = ChatRepository(db)

    async def create_room(self, *, user_id: UUID, role: str, room_id: UUID, tenant_id: UUID | None) -> CreateChatRoomResponse:
        room = await self.repo.get_room(room_id)
        if not room:
            raise HttpError(404, "Room not found")

        if role == "TENANT":
            tenant = user_id
            landlord = room.landlord_id
        elif role == "LANDLORD":
            landlord = user_id
            if not tenant_id:
                raise HttpError(400, "tenant_id is required for landlord")
            tenant = tenant_id
        else:
            raise HttpError(403, "Forbidden")

        now = datetime.now(timezone.utc)
        existing = await self.repo.get_chat_room_by_unique(tenant_id=tenant, landlord_id=landlord, room_id=room_id)
        if existing:
            chat_room = existing
            is_existing = True
        else:
            chat_room = await self.repo.create_chat_room(tenant_id=tenant, landlord_id=landlord, room_id=room_id, now=now)
            is_existing = False

        await self.repo.ensure_participant(chat_room_id=chat_room.id, user_id=tenant, now=now)
        await self.repo.ensure_participant(chat_room_id=chat_room.id, user_id=landlord, now=now)

        await self.repo.session.commit()
        await self.repo.session.refresh(chat_room)

        inbox_item = await self._build_inbox_item(user_id=user_id, chat_room=chat_room)
        return CreateChatRoomResponse(chat_room=inbox_item, is_existing=is_existing)

    async def list_rooms(
        self,
        *,
        user_id: UUID,
        cursor: str | None,
        limit: int,
        filter: str,
    ) -> ChatInboxResponse:
        limit = max(1, min(int(limit or 20), 50))
        unread_only = filter == "unread"

        c = decode_cursor(cursor)
        cursor_last_message_at = None
        cursor_id = None
        if c:
            cursor_id_raw = c.get("id")
            cursor_last_message_at_raw = c.get("last_message_at")
            try:
                cursor_id = UUID(cursor_id_raw) if cursor_id_raw else None
            except Exception:
                cursor_id = None
            try:
                cursor_last_message_at = datetime.fromisoformat(cursor_last_message_at_raw) if cursor_last_message_at_raw else None
            except Exception:
                cursor_last_message_at = None

        rooms = await self.repo.list_chat_rooms_for_user(
            user_id=user_id,
            limit=limit,
            cursor_last_message_at=cursor_last_message_at,
            cursor_id=cursor_id,
            unread_only=unread_only,
        )

        next_cursor = None
        if len(rooms) > limit:
            last = rooms.pop()
            next_cursor = encode_cursor(
                {"id": str(last.id), "last_message_at": last.last_message_at.isoformat() if last.last_message_at else None}
            )

        items = await self._build_inbox_items(user_id=user_id, chat_rooms=rooms)
        return ChatInboxResponse(data=items, next_cursor=next_cursor)

    async def get_room_detail(self, *, user_id: UUID, chat_room_id: UUID) -> ChatRoomDetailResponse:
        chat_room = await self.repo.get_chat_room(chat_room_id)
        if not chat_room:
            raise HttpError(404, "Chat room not found")
        if user_id not in {chat_room.tenant_id, chat_room.landlord_id}:
            raise HttpError(403, "Forbidden")

        other_id = chat_room.landlord_id if user_id == chat_room.tenant_id else chat_room.tenant_id
        profiles = await self.repo.get_profiles_by_user_ids([other_id])
        p = profiles.get(other_id)
        if not p:
            raise HttpError(404, "User not found")

        is_online = await self._is_online(other_id)
        participant = ChatParticipantBrief(id=other_id, full_name=p.full_name, avatar_url=p.avatar_url, is_online=is_online)

        room = None
        if chat_room.room_id:
            rooms = await self.repo.get_rooms_by_ids([chat_room.room_id])
            images = await self.repo.get_room_images_by_room_ids([chat_room.room_id])
            rm = rooms.get(chat_room.room_id)
            if rm:
                thumbnail = images.get(rm.id, [None])[0].image_url if images.get(rm.id) else None
                room = ChatRoomBrief(id=rm.id, title=rm.title, thumbnail=thumbnail)

        is_blocked = await self.repo.is_blocked_for_user(chat_room_id=chat_room.id, user_id=user_id)
        return ChatRoomDetailResponse(id=chat_room.id, participant=participant, room=room, is_blocked=is_blocked)

    async def get_messages(
        self,
        *,
        user_id: UUID,
        chat_room_id: UUID,
        cursor: str | None,
        limit: int,
        before_message_id: UUID | None,
    ) -> ChatMessagesResponse:
        chat_room = await self.repo.get_chat_room(chat_room_id)
        if not chat_room:
            raise HttpError(404, "Chat room not found")
        if user_id not in {chat_room.tenant_id, chat_room.landlord_id}:
            raise HttpError(403, "Forbidden")

        limit = max(1, min(int(limit or 20), 50))
        c = decode_cursor(cursor)
        cursor_created_at = None
        cursor_id = None
        if c:
            cursor_id_raw = c.get("id")
            cursor_created_at_raw = c.get("created_at")
            try:
                cursor_id = UUID(cursor_id_raw) if cursor_id_raw else None
            except Exception:
                cursor_id = None
            try:
                cursor_created_at = datetime.fromisoformat(cursor_created_at_raw) if cursor_created_at_raw else None
            except Exception:
                cursor_created_at = None

        messages = await self.repo.get_messages(
            chat_room_id=chat_room_id,
            limit=limit,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
            before_message_id=before_message_id,
        )

        next_cursor = None
        if len(messages) > limit:
            last = messages.pop()
            next_cursor = encode_cursor({"id": str(last.id), "created_at": last.created_at.isoformat()})

        data = [
            ChatMessageItem(
                id=m.id,
                sender_id=m.sender_id,
                message_type=m.message_type,
                content=m.message,
                image_url=m.image_url,
                is_read=bool(m.is_read),
                created_at=m.created_at,
            )
            for m in messages
        ]
        return ChatMessagesResponse(data=data, next_cursor=next_cursor)

    async def mark_read(self, *, user_id: UUID, chat_room_id: UUID, message_id: UUID) -> None:
        chat_room = await self.repo.get_chat_room(chat_room_id)
        if not chat_room:
            raise HttpError(404, "Chat room not found")
        if user_id not in {chat_room.tenant_id, chat_room.landlord_id}:
            raise HttpError(403, "Forbidden")

        msg = await self.repo.get_message(chat_room_id=chat_room_id, message_id=message_id)
        if not msg:
            raise HttpError(404, "Message not found")

        now = datetime.now(timezone.utc)
        participant = await self.repo.ensure_participant(chat_room_id=chat_room_id, user_id=user_id, now=now)
        participant.last_read_at = msg.created_at
        await self.repo.mark_read_up_to(chat_room_id=chat_room_id, reader_id=user_id, up_to_created_at=msg.created_at, now=now)
        await self.repo.session.commit()

        redis = await get_redis()
        await redis.delete(f"chat:unread_count:{user_id}")

    async def total_unread_count(self, *, user_id: UUID) -> int:
        redis = await get_redis()
        cache_key = f"chat:unread_count:{user_id}"
        cached = await redis.get(cache_key)
        if cached is not None:
            try:
                return int(cached)
            except Exception:
                pass
        count = await self.repo.total_unread_count(user_id=user_id)
        await redis.setex(cache_key, 30, str(count))
        return count

    async def presign_chat_image(self, *, file_name: str, content_type: str) -> PresignChatImageResponse:
        service = S3UploadService()
        result = service.generate_presigned_upload_url(folder="chat", file_name=file_name, content_type=content_type)
        return PresignChatImageResponse(upload_url=result.upload_url, file_url=result.file_url, object_key=result.object_key)

    async def delete_room(self, *, user_id: UUID, chat_room_id: UUID) -> None:
        chat_room = await self.repo.get_chat_room(chat_room_id)
        if not chat_room:
            raise HttpError(404, "Chat room not found")
        if user_id not in {chat_room.tenant_id, chat_room.landlord_id}:
            raise HttpError(403, "Forbidden")
        now = datetime.now(timezone.utc)
        await self.repo.ensure_deleted(chat_room_id=chat_room_id, user_id=user_id, now=now)
        await self.repo.session.commit()

    async def block_user(self, *, user_id: UUID, chat_room_id: UUID) -> None:
        chat_room = await self.repo.get_chat_room(chat_room_id)
        if not chat_room:
            raise HttpError(404, "Chat room not found")
        if user_id not in {chat_room.tenant_id, chat_room.landlord_id}:
            raise HttpError(403, "Forbidden")

        blocked_id = chat_room.landlord_id if user_id == chat_room.tenant_id else chat_room.tenant_id
        now = datetime.now(timezone.utc)
        await self.repo.ensure_block(chat_room_id=chat_room_id, blocker_id=user_id, blocked_id=blocked_id, now=now)
        await self.repo.session.commit()

    async def report_user(self, *, user_id: UUID, chat_room_id: UUID, reason: str) -> None:
        chat_room = await self.repo.get_chat_room(chat_room_id)
        if not chat_room:
            raise HttpError(404, "Chat room not found")
        if user_id not in {chat_room.tenant_id, chat_room.landlord_id}:
            raise HttpError(403, "Forbidden")
        now = datetime.now(timezone.utc)
        await self.repo.create_report(chat_room_id=chat_room_id, reporter_id=user_id, reason=reason, now=now)
        await self.repo.session.commit()

    async def _build_inbox_item(self, *, user_id: UUID, chat_room) -> ChatInboxItem:
        items = await self._build_inbox_items(user_id=user_id, chat_rooms=[chat_room])
        return items[0]

    async def _build_inbox_items(self, *, user_id: UUID, chat_rooms: list) -> list[ChatInboxItem]:
        if not chat_rooms:
            return []

        other_ids: list[UUID] = []
        room_ids: list[UUID] = []
        chat_room_ids: list[UUID] = []
        for r in chat_rooms:
            chat_room_ids.append(r.id)
            other_ids.append(r.landlord_id if user_id == r.tenant_id else r.tenant_id)
            if r.room_id:
                room_ids.append(r.room_id)

        profiles = await self.repo.get_profiles_by_user_ids(other_ids)
        rooms_map = await self.repo.get_rooms_by_ids(room_ids)
        images_map = await self.repo.get_room_images_by_room_ids(room_ids)
        unread_map = await self.repo.unread_count_by_room_ids(user_id=user_id, room_ids=chat_room_ids)
        online_map = await self._online_status_by_user_ids(other_ids)

        out: list[ChatInboxItem] = []
        for r in chat_rooms:
            other_id = r.landlord_id if user_id == r.tenant_id else r.tenant_id
            p = profiles.get(other_id)
            if not p:
                raise HttpError(404, "User not found")

            participant = ChatParticipantBrief(
                id=other_id,
                full_name=p.full_name,
                avatar_url=p.avatar_url,
                is_online=online_map.get(other_id, False),
            )

            room = None
            if r.room_id:
                rm = rooms_map.get(r.room_id)
                if rm:
                    imgs = images_map.get(rm.id) or []
                    thumbnail = imgs[0].image_url if imgs else None
                    room = ChatRoomBrief(id=rm.id, title=rm.title, thumbnail=thumbnail)

            last_message = None
            if r.last_message_id and r.last_message_at:
                last_message = ChatLastMessageBrief(
                    id=r.last_message_id,
                    content=r.last_message,
                    created_at=r.last_message_at,
                )

            out.append(
                ChatInboxItem(
                    id=r.id,
                    participant=participant,
                    room=room,
                    last_message=last_message,
                    unread_count=unread_map.get(r.id, 0),
                )
            )
        return out

    async def _is_online(self, user_id: UUID) -> bool:
        redis = await get_redis()
        v = await redis.get(f"chat:presence:{user_id}")
        return v == "1"

    async def _online_status_by_user_ids(self, user_ids: list[UUID]) -> dict[UUID, bool]:
        if not user_ids:
            return {}
        redis = await get_redis()
        keys = [f"chat:presence:{uid}" for uid in user_ids]
        values = await redis.mget(keys)
        out: dict[UUID, bool] = {}
        for uid, v in zip(user_ids, values):
            out[uid] = v == "1"
        return out
