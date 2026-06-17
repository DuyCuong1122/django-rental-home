from ninja import Router, Query
from ninja.errors import HttpError
from typing import List
from app.schemas.room import RoomCreate, RoomResponse, RoomDetailResponse
from app.api.deps import JWTAuth
from app.services.room import RoomService
from app.core.database import AsyncSessionLocal
from uuid import UUID
from app.schemas.room import NearbyRoomsQuery, RecommendedRoomsQuery, RecentlyAddedRoomsQuery

room_router = Router(tags=["Rooms"])

@room_router.post("/", response={201: RoomResponse}, auth=JWTAuth())
async def create_room(request, payload: RoomCreate):
    role = request.auth.get("role")
    if role not in ["LANDLORD", "ADMIN"]:
        raise HttpError(403, "Only landlords can create rooms")
        
    landlord_id = UUID(request.auth.get("sub"))
    async with AsyncSessionLocal() as db:
        service = RoomService(db)
        room = await service.create_room(landlord_id, payload)
        return 201, room

@room_router.get("/recent", response=List[RoomResponse])
async def get_recent_rooms(request, query: Query[RecentlyAddedRoomsQuery]):
    async with AsyncSessionLocal() as db:
        service = RoomService(db)
        return await service.get_recently_added(query)


@room_router.get("/recommended", response=List[RoomResponse])
async def get_recommended_rooms(request, query: Query[RecommendedRoomsQuery]):
    async with AsyncSessionLocal() as db:
        service = RoomService(db)
        return await service.get_recommended(query)


@room_router.get("/nearby", response=List[RoomResponse])
async def get_nearby_rooms(request, query: Query[NearbyRoomsQuery]):
    async with AsyncSessionLocal() as db:
        service = RoomService(db)
        return await service.get_nearby(query)


@room_router.get("/{uuid:room_id}", response=RoomDetailResponse)
async def get_room(request, room_id: UUID):
    async with AsyncSessionLocal() as db:
        service = RoomService(db)
        try:
            return await service.get_room_detail(room_id)
        except ValueError as e:
            raise HttpError(404, str(e))
