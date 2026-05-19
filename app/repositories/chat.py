from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import ChatMessage, ChatParticipant, ChatReport, ChatRoom, ChatRoomBlock, ChatRoomDeletion
from app.models.room import Room, RoomImage
from app.models.user import Profile, User


class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_room(self, room_id: UUID) -> Room | None:
        stmt = select(Room).options(selectinload(Room.images)).where(Room.id == room_id, Room.is_deleted == False)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_user(self, user_id: UUID) -> User | None:
        stmt = select(User).options(selectinload(User.profile)).where(User.id == user_id, User.is_deleted == False)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_chat_room_by_unique(self, *, tenant_id: UUID, landlord_id: UUID, room_id: UUID | None) -> ChatRoom | None:
        stmt = select(ChatRoom).where(
            ChatRoom.tenant_id == tenant_id,
            ChatRoom.landlord_id == landlord_id,
            ChatRoom.room_id == room_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_chat_room(self, *, tenant_id: UUID, landlord_id: UUID, room_id: UUID | None, now: datetime) -> ChatRoom:
        chat_room = ChatRoom(
            tenant_id=tenant_id,
            landlord_id=landlord_id,
            room_id=room_id,
            last_message=None,
            last_message_at=now,
        )
        self.session.add(chat_room)
        await self.session.flush()
        return chat_room

    async def get_participant(self, *, chat_room_id: UUID, user_id: UUID) -> ChatParticipant | None:
        stmt = select(ChatParticipant).where(ChatParticipant.chat_room_id == chat_room_id, ChatParticipant.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def ensure_participant(self, *, chat_room_id: UUID, user_id: UUID, now: datetime) -> ChatParticipant:
        existing = await self.get_participant(chat_room_id=chat_room_id, user_id=user_id)
        if existing:
            return existing
        participant = ChatParticipant(chat_room_id=chat_room_id, user_id=user_id, joined_at=now, last_read_at=None)
        self.session.add(participant)
        await self.session.flush()
        return participant

    async def get_chat_room(self, chat_room_id: UUID) -> ChatRoom | None:
        stmt = select(ChatRoom).where(ChatRoom.id == chat_room_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_chat_rooms_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
        cursor_last_message_at: datetime | None,
        cursor_id: UUID | None,
        unread_only: bool,
    ) -> list[ChatRoom]:
        deleted_exists = (
            exists(select(1).where(ChatRoomDeletion.chat_room_id == ChatRoom.id, ChatRoomDeletion.user_id == user_id))
            .correlate(ChatRoom)
        )
        stmt = select(ChatRoom).where(or_(ChatRoom.tenant_id == user_id, ChatRoom.landlord_id == user_id), ~deleted_exists)

        if cursor_last_message_at and cursor_id:
            stmt = stmt.where(
                or_(
                    ChatRoom.last_message_at < cursor_last_message_at,
                    and_(ChatRoom.last_message_at == cursor_last_message_at, ChatRoom.id < cursor_id),
                )
            )

        stmt = stmt.order_by(ChatRoom.last_message_at.desc().nullslast(), ChatRoom.id.desc()).limit(limit + 1)
        result = await self.session.execute(stmt)
        rooms = result.scalars().all()

        if unread_only and rooms:
            room_ids = [r.id for r in rooms]
            unread_stmt = (
                select(ChatMessage.chat_room_id)
                .where(
                    ChatMessage.chat_room_id.in_(room_ids),
                    ChatMessage.sender_id != user_id,
                    ChatMessage.is_read == False,
                )
                .group_by(ChatMessage.chat_room_id)
            )
            unread_res = await self.session.execute(unread_stmt)
            unread_room_ids = {row[0] for row in unread_res.all()}
            rooms = [r for r in rooms if r.id in unread_room_ids]

        return rooms

    async def get_profiles_by_user_ids(self, user_ids: list[UUID]) -> dict[UUID, Profile]:
        if not user_ids:
            return {}
        stmt = select(Profile).where(Profile.user_id.in_(user_ids))
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        return {p.user_id: p for p in items}

    async def get_room_images_by_room_ids(self, room_ids: list[UUID]) -> dict[UUID, list[RoomImage]]:
        if not room_ids:
            return {}
        stmt = (
            select(RoomImage)
            .where(RoomImage.room_id.in_(room_ids))
            .order_by(RoomImage.room_id.asc(), RoomImage.sort_order.asc(), RoomImage.created_at.asc())
        )
        result = await self.session.execute(stmt)
        images = result.scalars().all()
        out: dict[UUID, list[RoomImage]] = {}
        for img in images:
            out.setdefault(img.room_id, []).append(img)
        return out

    async def get_rooms_by_ids(self, room_ids: list[UUID]) -> dict[UUID, Room]:
        if not room_ids:
            return {}
        stmt = select(Room).where(Room.id.in_(room_ids), Room.is_deleted == False)
        result = await self.session.execute(stmt)
        rooms = result.scalars().all()
        return {r.id: r for r in rooms}

    async def unread_count_by_room_ids(self, *, user_id: UUID, room_ids: list[UUID]) -> dict[UUID, int]:
        if not room_ids:
            return {}
        stmt = (
            select(ChatMessage.chat_room_id, func.count(ChatMessage.id))
            .where(
                ChatMessage.chat_room_id.in_(room_ids),
                ChatMessage.sender_id != user_id,
                ChatMessage.is_read == False,
            )
            .group_by(ChatMessage.chat_room_id)
        )
        result = await self.session.execute(stmt)
        return {row[0]: int(row[1]) for row in result.all()}

    async def get_messages(
        self,
        *,
        chat_room_id: UUID,
        limit: int,
        cursor_created_at: datetime | None,
        cursor_id: UUID | None,
        before_message_id: UUID | None,
    ) -> list[ChatMessage]:
        if before_message_id:
            stmt_before = select(ChatMessage.created_at, ChatMessage.id).where(
                ChatMessage.id == before_message_id, ChatMessage.chat_room_id == chat_room_id
            )
            before_res = await self.session.execute(stmt_before)
            before_row = before_res.first()
            if before_row:
                cursor_created_at = before_row[0]
                cursor_id = before_row[1]

        stmt = select(ChatMessage).where(ChatMessage.chat_room_id == chat_room_id)
        if cursor_created_at and cursor_id:
            stmt = stmt.where(
                or_(
                    ChatMessage.created_at < cursor_created_at,
                    and_(ChatMessage.created_at == cursor_created_at, ChatMessage.id < cursor_id),
                )
            )
        stmt = stmt.order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(limit + 1)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_message(self, *, chat_room_id: UUID, message_id: UUID) -> ChatMessage | None:
        stmt = select(ChatMessage).where(ChatMessage.chat_room_id == chat_room_id, ChatMessage.id == message_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def mark_read_up_to(self, *, chat_room_id: UUID, reader_id: UUID, up_to_created_at: datetime, now: datetime) -> int:
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.chat_room_id == chat_room_id,
                ChatMessage.sender_id != reader_id,
                ChatMessage.is_read == False,
                ChatMessage.created_at <= up_to_created_at,
            )
            .order_by(ChatMessage.created_at.asc())
        )
        result = await self.session.execute(stmt)
        msgs = result.scalars().all()
        for m in msgs:
            m.is_read = True
            m.read_at = now
        return len(msgs)

    async def total_unread_count(self, *, user_id: UUID) -> int:
        stmt = (
            select(func.count(ChatMessage.id))
            .select_from(ChatMessage)
            .join(ChatRoom, ChatRoom.id == ChatMessage.chat_room_id)
            .where(
                or_(ChatRoom.tenant_id == user_id, ChatRoom.landlord_id == user_id),
                ChatMessage.sender_id != user_id,
                ChatMessage.is_read == False,
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def ensure_deleted(self, *, chat_room_id: UUID, user_id: UUID, now: datetime) -> None:
        stmt = select(ChatRoomDeletion).where(ChatRoomDeletion.chat_room_id == chat_room_id, ChatRoomDeletion.user_id == user_id)
        result = await self.session.execute(stmt)
        existing = result.scalars().first()
        if existing:
            return
        deletion = ChatRoomDeletion(chat_room_id=chat_room_id, user_id=user_id, deleted_at=now)
        self.session.add(deletion)
        await self.session.flush()

    async def get_block(self, *, chat_room_id: UUID, blocker_id: UUID, blocked_id: UUID) -> ChatRoomBlock | None:
        stmt = select(ChatRoomBlock).where(
            ChatRoomBlock.chat_room_id == chat_room_id,
            ChatRoomBlock.blocker_id == blocker_id,
            ChatRoomBlock.blocked_id == blocked_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def ensure_block(self, *, chat_room_id: UUID, blocker_id: UUID, blocked_id: UUID, now: datetime) -> None:
        existing = await self.get_block(chat_room_id=chat_room_id, blocker_id=blocker_id, blocked_id=blocked_id)
        if existing:
            return
        b = ChatRoomBlock(chat_room_id=chat_room_id, blocker_id=blocker_id, blocked_id=blocked_id, created_at=now)
        self.session.add(b)
        await self.session.flush()

    async def is_blocked_for_user(self, *, chat_room_id: UUID, user_id: UUID) -> bool:
        stmt = select(func.count(ChatRoomBlock.id)).where(
            ChatRoomBlock.chat_room_id == chat_room_id,
            or_(ChatRoomBlock.blocker_id == user_id, ChatRoomBlock.blocked_id == user_id),
        )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0) > 0

    async def create_report(self, *, chat_room_id: UUID, reporter_id: UUID, reason: str, now: datetime) -> None:
        r = ChatReport(chat_room_id=chat_room_id, reporter_id=reporter_id, reason=reason, created_at=now)
        self.session.add(r)
        await self.session.flush()
