import json
from uuid import UUID
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.room import RoomRepository
from app.schemas.room import (
    RoomCreate,
    SearchQuery,
    RoomResponse,
    RoomDetailResponse,
    NearbyRoomsQuery,
    RecommendedRoomsQuery,
    RecentlyAddedRoomsQuery,
)
from app.core.redis import get_redis
from app.core.business_metrics import ROOMS_CREATED_TOTAL, ROOM_DETAIL_VIEWS_TOTAL, ROOM_LIST_TOTAL

class RoomService:
    def __init__(self, db: AsyncSession):
        self.repo = RoomRepository(db)

    async def create_room(self, landlord_id: UUID, room_in: RoomCreate) -> RoomResponse:
        try:
            room = await self.repo.create_room(landlord_id, room_in)
            ROOMS_CREATED_TOTAL.labels(result="success", status=str(getattr(room, "status", "unknown"))).inc()
            return room
        except Exception:
            ROOMS_CREATED_TOTAL.labels(result="failure", status="unknown").inc()
            raise

    async def get_room_detail(self, room_id: UUID) -> RoomDetailResponse:
        redis = await get_redis()
        cache_key = f"room:detail:{room_id}"
        
        # Try Cache
        cached_data = await redis.get(cache_key)
        if cached_data:
            data = json.loads(cached_data)
            # Increment view count in redis
            await redis.incr(f"room:views:{room_id}")
            ROOM_DETAIL_VIEWS_TOTAL.inc()
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
        ROOM_DETAIL_VIEWS_TOTAL.inc()
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
            ROOM_LIST_TOTAL.labels(kind="search", cache="hit").inc()
            return [RoomResponse(**item) for item in json.loads(cached_data)]
            
        rooms = await self.repo.search_rooms(query)
        rooms_resp = [RoomResponse.model_validate(r) for r in rooms]
        ROOM_LIST_TOTAL.labels(kind="search", cache="miss").inc()
        
        # Cache for 2 minutes
        await redis.setex(cache_key, 120, json.dumps([r.model_dump(mode='json') for r in rooms_resp]))
        
        return rooms_resp

    async def get_recently_added(self, query: RecentlyAddedRoomsQuery) -> List[RoomResponse]:
        redis = await get_redis()
        query_dict = query.model_dump(exclude_none=True)
        cache_key = f"room:recent:{hash(frozenset(query_dict.items()))}"

        cached_data = await redis.get(cache_key)
        if cached_data:
            ROOM_LIST_TOTAL.labels(kind="recent", cache="hit").inc()
            return [RoomResponse(**item) for item in json.loads(cached_data)]

        rooms = await self.repo.get_recently_added(query)
        rooms_resp = [RoomResponse.model_validate(r) for r in rooms]
        ROOM_LIST_TOTAL.labels(kind="recent", cache="miss").inc()
        await redis.setex(cache_key, 60, json.dumps([r.model_dump(mode="json") for r in rooms_resp]))
        return rooms_resp

    async def get_recommended(self, query: RecommendedRoomsQuery) -> List[RoomResponse]:
        redis = await get_redis()
        query_dict = query.model_dump(exclude_none=True)
        cache_key = f"room:recommended:{hash(frozenset(query_dict.items()))}"

        cached_data = await redis.get(cache_key)
        if cached_data:
            ROOM_LIST_TOTAL.labels(kind="recommended", cache="hit").inc()
            return [RoomResponse(**item) for item in json.loads(cached_data)]

        rooms = await self.repo.get_recommended(query)
        rooms_resp = [RoomResponse.model_validate(r) for r in rooms]
        ROOM_LIST_TOTAL.labels(kind="recommended", cache="miss").inc()
        await redis.setex(cache_key, 60, json.dumps([r.model_dump(mode="json") for r in rooms_resp]))
        return rooms_resp

    async def get_nearby(self, query: NearbyRoomsQuery) -> List[RoomResponse]:
        redis = await get_redis()
        query_dict = query.model_dump(exclude_none=True)
        cache_key = f"room:nearby:{hash(frozenset(query_dict.items()))}"

        cached_data = await redis.get(cache_key)
        if cached_data:
            ROOM_LIST_TOTAL.labels(kind="nearby", cache="hit").inc()
            return [RoomResponse(**item) for item in json.loads(cached_data)]

        rooms = await self.repo.get_nearby(query)
        rooms_resp = [RoomResponse.model_validate(r) for r in rooms]
        ROOM_LIST_TOTAL.labels(kind="nearby", cache="miss").inc()
        await redis.setex(cache_key, 30, json.dumps([r.model_dump(mode="json") for r in rooms_resp]))
        return rooms_resp
