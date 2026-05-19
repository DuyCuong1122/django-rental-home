from uuid import UUID

from ninja import Router
from ninja.errors import HttpError

from app.api.deps import JWTAuth
from app.core.database import AsyncSessionLocal
from app.schemas.chat import (
    ChatInboxResponse,
    ChatMessagesResponse,
    ChatRoomDetailResponse,
    CreateChatRoomRequest,
    CreateChatRoomResponse,
    MarkReadRequest,
    PresignChatImageRequest,
    PresignChatImageResponse,
    ReportUserRequest,
    SimpleSuccessResponse,
    UnreadCountResponse,
)
from app.services.chat import ChatService


chat_router = Router(tags=["Chat"], auth=JWTAuth())


def _user_id_and_role(request) -> tuple[UUID, str]:
    if not request.auth:
        raise HttpError(401, "Unauthorized")
    raw = request.auth.get("sub")
    role = request.auth.get("role") or ""
    if not raw:
        raise HttpError(401, "Unauthorized")
    try:
        return UUID(raw), str(role)
    except Exception:
        raise HttpError(401, "Unauthorized")


@chat_router.post("/rooms", response=CreateChatRoomResponse)
async def create_room(request, payload: CreateChatRoomRequest):
    user_id, role = _user_id_and_role(request)
    async with AsyncSessionLocal() as db:
        service = ChatService(db)
        return await service.create_room(
            user_id=user_id,
            role=role,
            room_id=payload.room_id,
            tenant_id=payload.tenant_id,
        )


@chat_router.get("/rooms", response=ChatInboxResponse)
async def list_rooms(
    request,
    cursor: str | None = None,
    limit: int = 20,
    filter: str = "all",
):
    user_id, _role = _user_id_and_role(request)
    if filter not in {"all", "unread"}:
        raise HttpError(400, "Invalid filter")
    async with AsyncSessionLocal() as db:
        service = ChatService(db)
        return await service.list_rooms(user_id=user_id, cursor=cursor, limit=limit, filter=filter)


@chat_router.get("/rooms/{chat_room_id}", response=ChatRoomDetailResponse)
async def room_detail(request, chat_room_id: UUID):
    user_id, _role = _user_id_and_role(request)
    async with AsyncSessionLocal() as db:
        service = ChatService(db)
        return await service.get_room_detail(user_id=user_id, chat_room_id=chat_room_id)


@chat_router.get("/rooms/{chat_room_id}/messages", response=ChatMessagesResponse)
async def message_history(
    request,
    chat_room_id: UUID,
    cursor: str | None = None,
    limit: int = 20,
    before_message_id: UUID | None = None,
):
    user_id, _role = _user_id_and_role(request)
    async with AsyncSessionLocal() as db:
        service = ChatService(db)
        return await service.get_messages(
            user_id=user_id,
            chat_room_id=chat_room_id,
            cursor=cursor,
            limit=limit,
            before_message_id=before_message_id,
        )


@chat_router.post("/rooms/{chat_room_id}/read", response=SimpleSuccessResponse)
async def mark_read(request, chat_room_id: UUID, payload: MarkReadRequest):
    user_id, _role = _user_id_and_role(request)
    async with AsyncSessionLocal() as db:
        service = ChatService(db)
        await service.mark_read(user_id=user_id, chat_room_id=chat_room_id, message_id=payload.message_id)
        return SimpleSuccessResponse()


@chat_router.get("/unread-count", response=UnreadCountResponse)
async def unread_count(request):
    user_id, _role = _user_id_and_role(request)
    async with AsyncSessionLocal() as db:
        service = ChatService(db)
        count = await service.total_unread_count(user_id=user_id)
        return UnreadCountResponse(count=count)


@chat_router.post("/image/presigned-url", response=PresignChatImageResponse)
async def presign_chat_image(request, payload: PresignChatImageRequest):
    _user_id, _role = _user_id_and_role(request)
    async with AsyncSessionLocal() as db:
        service = ChatService(db)
        return await service.presign_chat_image(file_name=payload.file_name, content_type=payload.content_type)


@chat_router.delete("/rooms/{chat_room_id}", response=SimpleSuccessResponse)
async def delete_room(request, chat_room_id: UUID):
    user_id, _role = _user_id_and_role(request)
    async with AsyncSessionLocal() as db:
        service = ChatService(db)
        await service.delete_room(user_id=user_id, chat_room_id=chat_room_id)
        return SimpleSuccessResponse()


@chat_router.post("/rooms/{chat_room_id}/block", response=SimpleSuccessResponse)
async def block_user(request, chat_room_id: UUID):
    user_id, _role = _user_id_and_role(request)
    async with AsyncSessionLocal() as db:
        service = ChatService(db)
        await service.block_user(user_id=user_id, chat_room_id=chat_room_id)
        return SimpleSuccessResponse()


@chat_router.post("/report", response=SimpleSuccessResponse)
async def report_user(request, payload: ReportUserRequest):
    user_id, _role = _user_id_and_role(request)
    async with AsyncSessionLocal() as db:
        service = ChatService(db)
        await service.report_user(user_id=user_id, chat_room_id=payload.chat_room_id, reason=payload.reason)
        return SimpleSuccessResponse()
