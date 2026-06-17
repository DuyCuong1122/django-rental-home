import logging
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from app.core.redis import get_redis
from app.core.database import AsyncSessionLocal
from app.services.chat import ChatService
from ninja.errors import HttpError
from uuid import UUID
from app.core.business_metrics import WEBSOCKET_ACTIVE_CONNECTIONS, WEBSOCKET_ERRORS_TOTAL, WEBSOCKET_MESSAGES_TOTAL


logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        WEBSOCKET_MESSAGES_TOTAL.labels(namespace="chat", type="connect").inc()
        kwargs = self.scope.get("url_route", {}).get("kwargs") or {}
        self.chat_room_id = kwargs.get("chat_room_id") or kwargs.get("room_id")
        self.room_group_name = f"chat_{self.chat_room_id}"

        self.user_id = self.scope.get("user_id")
        if not self.user_id:
            WEBSOCKET_ERRORS_TOTAL.labels(namespace="chat", type="unauthorized").inc()
            await self.close(code=4401)
            return

        try:
            async with AsyncSessionLocal() as db:
                service = ChatService(db)
                chat_room = await service.repo.get_chat_room(self.chat_room_id)
                if not chat_room:
                    await self.close(code=4404)
                    return
                if self.user_id not in {chat_room.tenant_id, chat_room.landlord_id}:
                    await self.close(code=4403)
                    return
                if await service.repo.is_blocked_for_user(chat_room_id=chat_room.id, user_id=self.user_id):
                    await self.close(code=4403)
                    return
        except Exception:
            WEBSOCKET_ERRORS_TOTAL.labels(namespace="chat", type="connect_error").inc()
            await self.close(code=1011)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        WEBSOCKET_ACTIVE_CONNECTIONS.labels(namespace="chat").inc()

        redis = await get_redis()
        await redis.setex(f"user_online:{self.user_id}", 60, "1")
        logger.info("User online user_id=%s chat_room_id=%s", self.user_id, self.chat_room_id)
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "online_status", "user_id": str(self.user_id), "is_online": True},
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        try:
            WEBSOCKET_ACTIVE_CONNECTIONS.labels(namespace="chat").dec()
        except Exception:
            pass
        if getattr(self, "user_id", None):
            redis = await get_redis()
            await redis.delete(f"user_online:{self.user_id}")
            logger.info("User offline user_id=%s chat_room_id=%s", self.user_id, getattr(self, "chat_room_id", None))
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "online_status", "user_id": str(self.user_id), "is_online": False},
            )

    async def receive(self, text_data):
        WEBSOCKET_MESSAGES_TOTAL.labels(namespace="chat", type="receive").inc()
        try:
            data = json.loads(text_data)
        except Exception:
            WEBSOCKET_ERRORS_TOTAL.labels(namespace="chat", type="invalid_json").inc()
            await self.send(text_data=json.dumps({"type": "error", "message": "Invalid JSON"}))
            return

        event_type = data.get("type")
        if event_type in {"message", "send_message"}:
            WEBSOCKET_MESSAGES_TOTAL.labels(namespace="chat", type="message").inc()
            temp_id = data.get("temp_id")
            message_type = data.get("message_type") or "TEXT"
            content = data.get("content") or data.get("text")
            image_url = data.get("image_url")
            message_metadata = data.get("metadata")

            try:
                async with AsyncSessionLocal() as db:
                    service = ChatService(db)
                    item = await service.create_message(
                        user_id=self.user_id,
                        chat_room_id=UUID(str(self.chat_room_id)),
                        message_type=str(message_type),
                        content=content,
                        image_url=image_url,
                        message_metadata=message_metadata,
                    )
            except HttpError as e:
                WEBSOCKET_ERRORS_TOTAL.labels(namespace="chat", type="http_error").inc()
                await self.send(text_data=json.dumps({"type": "error", "message": str(e.message)}))
                return
            except Exception:
                WEBSOCKET_ERRORS_TOTAL.labels(namespace="chat", type="server_error").inc()
                await self.send(text_data=json.dumps({"type": "error", "message": "Internal server error"}))
                return

            redis = await get_redis()
            await redis.setex(f"user_online:{self.user_id}", 60, "1")

            payload = {
                "type": "message",
                "id": str(item.id),
                "temp_id": str(temp_id) if temp_id else None,
                "sender_id": str(item.sender_id),
                "message_type": item.message_type,
                "content": item.content,
                "message": item.content,
                "image_url": item.image_url,
                "created_at": item.created_at.isoformat(),
            }
            await self.channel_layer.group_send(self.room_group_name, {"type": "chat_message", "payload": payload})
            return

        if event_type == "typing":
            WEBSOCKET_MESSAGES_TOTAL.labels(namespace="chat", type="typing").inc()
            is_typing = bool(data.get("is_typing"))
            redis = await get_redis()
            await redis.setex(f"chat:typing:{self.chat_room_id}:{self.user_id}", 5, "1" if is_typing else "0")
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "user_typing", "user_id": str(self.user_id), "is_typing": is_typing},
            )
            return

        if event_type in {"read_receipt", "seen"}:
            WEBSOCKET_MESSAGES_TOTAL.labels(namespace="chat", type="seen").inc()
            message_id = data.get("message_id")
            if not message_id:
                WEBSOCKET_ERRORS_TOTAL.labels(namespace="chat", type="missing_message_id").inc()
                await self.send(text_data=json.dumps({"type": "error", "message": "message_id is required"}))
                return
            try:
                async with AsyncSessionLocal() as db:
                    service = ChatService(db)
                    await service.mark_read(
                        user_id=self.user_id,
                        chat_room_id=UUID(str(self.chat_room_id)),
                        message_id=UUID(str(message_id)),
                    )
            except HttpError as e:
                WEBSOCKET_ERRORS_TOTAL.labels(namespace="chat", type="http_error").inc()
                await self.send(text_data=json.dumps({"type": "error", "message": str(e.message)}))
                return
            except Exception:
                WEBSOCKET_ERRORS_TOTAL.labels(namespace="chat", type="server_error").inc()
                await self.send(text_data=json.dumps({"type": "error", "message": "Internal server error"}))
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "seen_event", "user_id": str(self.user_id), "message_id": str(message_id)},
            )
            return

        WEBSOCKET_ERRORS_TOTAL.labels(namespace="chat", type="unknown_event_type").inc()
        await self.send(text_data=json.dumps({"type": "error", "message": "Unknown event type"}))

    async def chat_message(self, event):
        payload = event.get("payload") or {}
        try:
            await self.send(text_data=json.dumps(payload))
        except Exception:
            return

    async def user_typing(self, event):
        try:
            await self.send(text_data=json.dumps({"type": "typing", "user_id": event["user_id"], "is_typing": event["is_typing"]}))
        except Exception:
            return

    async def seen_event(self, event):
        try:
            await self.send(
                text_data=json.dumps({"type": "seen", "user_id": event["user_id"], "message_id": event["message_id"]})
            )
        except Exception:
            return

    async def online_status(self, event):
        try:
            await self.send(
                text_data=json.dumps({"type": "online_status", "user_id": event["user_id"], "is_online": event["is_online"]})
            )
        except Exception:
            return
