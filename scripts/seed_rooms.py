from __future__ import annotations

import asyncio
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.room import Room, RoomImage
from app.models.user import Profile, User


CENTER_LAT = 21.0278
CENTER_LNG = 105.8342


def _rand_price(min_vnd: int, max_vnd: int) -> Decimal:
    return Decimal(str(random.randint(min_vnd, max_vnd)))


def _nearby_point() -> tuple[float, float]:
    lat = CENTER_LAT + random.uniform(-0.03, 0.03)
    lng = CENTER_LNG + random.uniform(-0.03, 0.03)
    return lat, lng


def _far_point() -> tuple[float, float]:
    candidates = [
        (10.7769, 106.7009),
        (16.0471, 108.2068),
        (20.8449, 106.6881),
        (22.8233, 104.9836),
    ]
    base_lat, base_lng = random.choice(candidates)
    return base_lat + random.uniform(-0.2, 0.2), base_lng + random.uniform(-0.2, 0.2)


async def _get_or_create_landlord(db) -> User:
    email = "seed_landlord@example.com"
    stmt = select(User).where(User.email == email, User.is_deleted == False)
    res = await db.execute(stmt)
    user = res.scalars().first()
    if user:
        return user

    user = User(
        email=email,
        password_hash=get_password_hash("Password123!"),
        role="LANDLORD",
        is_active=True,
        is_deleted=False,
    )
    db.add(user)
    await db.flush()

    profile = Profile(
        user_id=user.id,
        full_name="Seed Landlord",
        phone="0900000000",
    )
    db.add(profile)
    await db.commit()
    await db.refresh(user)
    return user


async def seed_rooms(total: int = 100, nearby_count: int = 10) -> None:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        landlord = await _get_or_create_landlord(db)

        rooms: list[Room] = []
        for i in range(total):
            is_near = i < nearby_count
            lat, lng = _nearby_point() if is_near else _far_point()

            province = "Hanoi" if is_near else random.choice(["HCM", "Da Nang", "Hai Phong", "Ha Giang"])
            district = "Hanoi" if is_near else random.choice(["District 1", "District 3", "Hai Chau", "Le Chan"])
            ward = "Ward 1"

            created_at = now - timedelta(minutes=(total - i))

            room = Room(
                id=uuid.uuid4(),
                landlord_id=landlord.id,
                title=f"Seed Room #{i + 1}",
                description="Auto seeded room for testing nearby/recommended/recent APIs.",
                monthly_price=_rand_price(2500000, 12000000),
                deposit=_rand_price(2500000, 12000000),
                electric_price=_rand_price(3000, 5000),
                water_price=_rand_price(10000, 20000),
                area=float(random.uniform(18.0, 45.0)),
                max_people=random.randint(1, 4),
                gender_preference=random.choice(["ANY", "MALE", "FEMALE"]),
                available_date=now + timedelta(days=random.randint(1, 30)),
                province=province,
                district=district,
                ward=ward,
                full_address=f"{random.randint(1, 300)} Seed Street, {district}, {province}",
                latitude=float(lat),
                longitude=float(lng),
                amenities={"wifi": True, "parking": bool(random.getrandbits(1)), "air_conditioner": True},
                rules={"pet_allowed": False, "cooking_allowed": True},
                status="APPROVED",
                is_deleted=False,
                created_at=created_at,
                updated_at=created_at,
            )
            rooms.append(room)
            db.add(room)

            for idx in range(random.randint(0, 2)):
                db.add(
                    RoomImage(
                        room_id=room.id,
                        image_url=f"https://example.com/seed-room/{room.id}/{idx}.jpg",
                        sort_order=idx,
                        created_at=created_at,
                    )
                )

        await db.commit()

    print(f"Seeded {total} rooms (nearby within ~10km: {nearby_count}).")
    print(
        "Try nearby query:\n"
        "curl --location 'http://10.0.60.75/api/v1/rooms/nearby?latitude=21.0278&longitude=105.8342&radius_km=10&limit=20&offset=0'"
    )


if __name__ == "__main__":
    asyncio.run(seed_rooms())
