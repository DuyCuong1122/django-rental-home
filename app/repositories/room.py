from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models.room import Room, RoomImage
from app.schemas.room import RoomCreate, SearchQuery, NearbyRoomsQuery, RecommendedRoomsQuery, RecentlyAddedRoomsQuery
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
        room = await self.get_room(db_room.id)
        return room or db_room

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

    async def get_recently_added(self, query: RecentlyAddedRoomsQuery) -> List[Room]:
        stmt = (
            select(Room)
            .options(selectinload(Room.images))
            .where(Room.is_deleted == False, Room.status == "APPROVED")
        )
        if query.province:
            stmt = stmt.where(Room.province == query.province)
        if query.district:
            stmt = stmt.where(Room.district == query.district)

        stmt = stmt.order_by(Room.created_at.desc()).offset(query.offset).limit(query.limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_recommended(self, query: RecommendedRoomsQuery) -> List[Room]:
        stmt = (
            select(Room)
            .options(selectinload(Room.images))
            .where(Room.is_deleted == False, Room.status == "APPROVED")
        )
        if query.province:
            stmt = stmt.where(Room.province == query.province)
        if query.district:
            stmt = stmt.where(Room.district == query.district)

        stmt = stmt.order_by(Room.updated_at.desc(), Room.created_at.desc()).offset(query.offset).limit(query.limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_nearby(self, query: NearbyRoomsQuery) -> List[Room]:
        lat0 = float(query.latitude)
        lon0 = float(query.longitude)

        lat = func.radians(Room.latitude)
        lon = func.radians(Room.longitude)
        lat0r = func.radians(lat0)
        lon0r = func.radians(lon0)
        cos_angle = (
            func.cos(lat0r) * func.cos(lat) * func.cos(lon - lon0r)
            + func.sin(lat0r) * func.sin(lat)
        )
        cos_angle = func.least(1.0, func.greatest(-1.0, cos_angle))
        distance_km = 6371.0 * func.acos(cos_angle)

        stmt = (
            select(Room)
            .options(selectinload(Room.images))
            .where(
                Room.is_deleted == False,
                Room.status == "APPROVED",
                Room.latitude.isnot(None),
                Room.longitude.isnot(None),
                distance_km <= float(query.radius_km),
            )
            .order_by(distance_km.asc(), Room.created_at.desc())
            .offset(query.offset)
            .limit(query.limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
