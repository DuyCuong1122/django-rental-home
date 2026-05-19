from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatParticipantBrief(BaseModel):
    id: UUID
    full_name: str
    avatar_url: str | None = None
    is_online: bool = False


class ChatRoomBrief(BaseModel):
    id: UUID
    title: str
    thumbnail: str | None = None


class ChatLastMessageBrief(BaseModel):
    id: UUID
    content: str | None = None
    created_at: datetime


class ChatInboxItem(BaseModel):
    id: UUID
    participant: ChatParticipantBrief
    room: ChatRoomBrief | None = None
    last_message: ChatLastMessageBrief | None = None
    unread_count: int = 0


class ChatInboxResponse(BaseModel):
    data: list[ChatInboxItem]
    next_cursor: str | None = None


class CreateChatRoomRequest(BaseModel):
    room_id: UUID
    tenant_id: UUID | None = None


class CreateChatRoomResponse(BaseModel):
    success: bool = True
    chat_room: ChatInboxItem
    is_existing: bool


class ChatRoomDetailResponse(BaseModel):
    id: UUID
    participant: ChatParticipantBrief
    room: ChatRoomBrief | None = None
    is_blocked: bool = False


class ChatMessageItem(BaseModel):
    id: UUID
    sender_id: UUID
    message_type: str
    content: str | None = None
    image_url: str | None = None
    is_read: bool = False
    created_at: datetime


class ChatMessagesResponse(BaseModel):
    data: list[ChatMessageItem]
    next_cursor: str | None = None


class MarkReadRequest(BaseModel):
    message_id: UUID


class SimpleSuccessResponse(BaseModel):
    success: bool = True


class UnreadCountResponse(BaseModel):
    count: int = 0


class PresignChatImageRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=255)


class PresignChatImageResponse(BaseModel):
    upload_url: str
    file_url: str
    object_key: str


class ReportUserRequest(BaseModel):
    chat_room_id: UUID
    reason: str = Field(min_length=1, max_length=255)


class ValidationErrorResponse(BaseModel):
    success: bool = False
    message: str = "Validation error"
    errors: dict[str, list[str]]


class ChatRoomModel(BaseModel):
    id: UUID
    room_id: UUID | None = None
    tenant_id: UUID
    landlord_id: UUID
    last_message: str | None = None
    last_message_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageModel(BaseModel):
    id: UUID
    chat_room_id: UUID
    sender_id: UUID
    message_type: str
    message: str | None = None
    image_url: str | None = None
    metadata: dict | None = Field(default=None, validation_alias="message_metadata")
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
