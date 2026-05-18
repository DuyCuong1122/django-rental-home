from ninja import Router, Query
from typing import List
from app.schemas.room import SearchQuery, RoomResponse
from app.services.room import RoomService
from app.core.database import AsyncSessionLocal

search_router = Router(tags=["Search"])

@search_router.get("/rooms", response=List[RoomResponse])
async def search_rooms(request, query: Query[SearchQuery]):
    async with AsyncSessionLocal() as db:
        service = RoomService(db)
        return await service.search_rooms(query)
