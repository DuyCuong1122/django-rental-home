import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ChatMessageType(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    SYSTEM = "SYSTEM"


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=True)

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    landlord_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    last_message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id"), nullable=True)
    last_message = Column(Text, nullable=True)
    last_message_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    tenant = relationship("User", foreign_keys=[tenant_id])
    landlord = relationship("User", foreign_keys=[landlord_id])
    room = relationship("Room")

    participants = relationship("ChatParticipant", back_populates="chat_room", cascade="all, delete-orphan")
    messages = relationship(
        "ChatMessage",
        back_populates="chat_room",
        cascade="all, delete-orphan",
        foreign_keys="ChatMessage.chat_room_id",
    )
    last_message_obj = relationship("ChatMessage", foreign_keys=[last_message_id], post_update=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "landlord_id", "room_id", name="uq_chat_rooms_tenant_landlord_room"),
        Index(
            "uq_chat_rooms_tenant_landlord_null_room",
            "tenant_id",
            "landlord_id",
            unique=True,
            postgresql_where=room_id.is_(None),
        ),
        Index("ix_chat_rooms_last_message_at", "last_message_at"),
    )


class ChatParticipant(Base):
    __tablename__ = "chat_participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_room_id = Column(UUID(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    last_read_at = Column(DateTime(timezone=True), nullable=True)
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    chat_room = relationship("ChatRoom", back_populates="participants")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("chat_room_id", "user_id", name="uq_chat_participants_room_user"),
        Index("ix_chat_participants_chat_room_id", "chat_room_id"),
        Index("ix_chat_participants_user_id", "user_id"),
    )


class ChatRoomDeletion(Base):
    __tablename__ = "chat_room_deletions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_room_id = Column(UUID(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    deleted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("chat_room_id", "user_id", name="uq_chat_room_deletions_room_user"),
        Index("ix_chat_room_deletions_user_id", "user_id"),
        Index("ix_chat_room_deletions_chat_room_id", "chat_room_id"),
    )


class ChatRoomBlock(Base):
    __tablename__ = "chat_room_blocks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_room_id = Column(UUID(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False)
    blocker_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    blocked_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("chat_room_id", "blocker_id", "blocked_id", name="uq_chat_room_blocks_room_blocker_blocked"),
        Index("ix_chat_room_blocks_chat_room_id", "chat_room_id"),
        Index("ix_chat_room_blocks_blocker_id", "blocker_id"),
        Index("ix_chat_room_blocks_blocked_id", "blocked_id"),
    )


class ChatReport(Base):
    __tablename__ = "chat_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_room_id = Column(UUID(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False)
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reason = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_chat_reports_chat_room_id", "chat_room_id"),
        Index("ix_chat_reports_reporter_id", "reporter_id"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_room_id = Column(UUID(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    message_type = Column(String(20), nullable=False, default=ChatMessageType.TEXT.value)
    message = Column(Text, nullable=True)
    image_url = Column(String(2048), nullable=True)
    message_metadata = Column("metadata", JSONB, nullable=True)

    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    chat_room = relationship("ChatRoom", back_populates="messages", foreign_keys=[chat_room_id])
    sender = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "message_type IN ('TEXT', 'IMAGE', 'SYSTEM')",
            name="ck_chat_messages_message_type",
        ),
        Index("ix_chat_messages_room_created_at", "chat_room_id", "created_at"),
    )
