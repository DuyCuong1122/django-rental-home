import json
from channels.generic.websocket import AsyncWebsocketConsumer
from app.core.redis import get_redis

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        
        # In a real app, you would authenticate the user here
        # user = self.scope.get("user")
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'message':
            # Save message to DB asynchronously, trigger push notification if offline
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': data.get('content'),
                    'sender_id': data.get('sender_id')
                }
            )
        elif message_type == 'typing':
            redis = await get_redis()
            user_id = data.get('user_id')
            await redis.setex(f"chat:typing:{self.room_id}:{user_id}", 5, "true")
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_typing',
                    'user_id': user_id,
                    'is_typing': data.get('is_typing')
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'sender_id': event['sender_id']
        }))

    async def user_typing(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'is_typing': event['is_typing']
        }))
