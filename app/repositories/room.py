from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models.room import Room, RoomImage
from app.schemas.room import RoomCreate, SearchQuery
from uuid import UUID

class RoomRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_room(self, landlord_id: UUID, room_in: RoomCreate) -> Room:
        db_room = Room(
            landlord_id=landlord_id,
            title=room_in.title,
            description=room_in.description,
            monthly_price=room_in.monthly_price,
            deposit=room_in.deposit,
            electric_price=room_in.electric_price,
            water_price=room_in.water_price,
            area=room_in.area,
            max_people=room_in.max_people,
            gender_preference=room_in.gender_preference,
            available_date=room_in.available_date,
            province=room_in.province,
            district=room_in.district,
            ward=room_in.ward,
            full_address=room_in.full_address,
            latitude=room_in.latitude,
            longitude=room_in.longitude,
            amenities=room_in.amenities,
            rules=room_in.rules,
            status="PENDING"
        )
        self.session.add(db_room)
        await self.session.flush()

        for idx, url in enumerate(room_in.image_urls):
            db_image = RoomImage(room_id=db_room.id, image_url=url, sort_order=idx)
            self.session.add(db_image)

        await self.session.commit()
        await self.session.refresh(db_room)
        return db_room

    async def get_room(self, room_id: UUID) -> Optional[Room]:
        stmt = select(Room).options(selectinload(Room.images)).where(Room.id == room_id, Room.is_deleted == False)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def search_rooms(self, query: SearchQuery) -> List[Room]:
        stmt = select(Room).options(selectinload(Room.images)).where(
            Room.is_deleted == False,
            Room.status == "APPROVED"
        )
        
        if query.keyword:
            # Note: In production, use pg_trgm for full text search.
            # Here we use ILIKE as a fallback.
            search_term = f"%{query.keyword}%"
            stmt = stmt.where(or_(Room.title.ilike(search_term), Room.description.ilike(search_term)))
            
        if query.district:
            stmt = stmt.where(Room.district == query.district)
        if query.ward:
            stmt = stmt.where(Room.ward == query.ward)
        if query.min_price is not None:
            stmt = stmt.where(Room.monthly_price >= query.min_price)
        if query.max_price is not None:
            stmt = stmt.where(Room.monthly_price <= query.max_price)
        if query.min_area is not None:
            stmt = stmt.where(Room.area >= query.min_area)
        if query.max_area is not None:
            stmt = stmt.where(Room.area <= query.max_area)

        stmt = stmt.offset(query.offset).limit(query.limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
