from ninja import Router
from ninja.errors import HttpError
from app.schemas.room import RoomCreate, RoomResponse, RoomDetailResponse
from app.api.deps import JWTAuth
from app.services.room import RoomService
from app.core.database import AsyncSessionLocal
from uuid import UUID

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

@room_router.get("/{room_id}", response=RoomDetailResponse)
async def get_room(request, room_id: UUID):
    async with AsyncSessionLocal() as db:
        service = RoomService(db)
        try:
            return await service.get_room_detail(room_id)
        except ValueError as e:
            raise HttpError(404, str(e))
