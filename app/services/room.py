import json
from uuid import UUID
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.room import RoomRepository
from app.schemas.room import RoomCreate, SearchQuery, RoomResponse, RoomDetailResponse
from app.core.redis import get_redis

class RoomService:
    def __init__(self, db: AsyncSession):
        self.repo = RoomRepository(db)

    async def create_room(self, landlord_id: UUID, room_in: RoomCreate) -> RoomResponse:
        room = await self.repo.create_room(landlord_id, room_in)
        return room

    async def get_room_detail(self, room_id: UUID) -> RoomDetailResponse:
        redis = await get_redis()
        cache_key = f"room:detail:{room_id}"
        
        # Try Cache
        cached_data = await redis.get(cache_key)
        if cached_data:
            data = json.loads(cached_data)
            # Increment view count in redis
            await redis.incr(f"room:views:{room_id}")
            data["view_count"] = int(await redis.get(f"room:views:{room_id}") or 0)
            data["favorite_count"] = int(await redis.get(f"room:favorites:{room_id}") or 0)
            return RoomDetailResponse(**data)
            
        # Fallback to DB
        room = await self.repo.get_room(room_id)
        if not room:
            raise ValueError("Room not found")
            
        # We need to serialize the SQLAlchemy model to a dict that Pydantic can load
        room_dict = RoomResponse.model_validate(room).model_dump(mode='json')
        
        # Cache for 5 minutes
        await redis.setex(cache_key, 300, json.dumps(room_dict))
        
        # Views and Favorites
        await redis.incr(f"room:views:{room_id}")
        room_dict["view_count"] = int(await redis.get(f"room:views:{room_id}") or 0)
        room_dict["favorite_count"] = int(await redis.get(f"room:favorites:{room_id}") or 0)
        
        return RoomDetailResponse(**room_dict)

    async def search_rooms(self, query: SearchQuery) -> List[RoomResponse]:
        redis = await get_redis()
        # Create a stable cache key
        query_dict = query.model_dump(exclude_none=True)
        cache_key = f"room:search:{hash(frozenset(query_dict.items()))}"
        
        cached_data = await redis.get(cache_key)
        if cached_data:
            return [RoomResponse(**item) for item in json.loads(cached_data)]
            
        rooms = await self.repo.search_rooms(query)
        rooms_resp = [RoomResponse.model_validate(r) for r in rooms]
        
        # Cache for 2 minutes
        await redis.setex(cache_key, 120, json.dumps([r.model_dump(mode='json') for r in rooms_resp]))
        
        return rooms_resp
