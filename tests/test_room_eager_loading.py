import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token


class DummySession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_create_room_endpoint_does_not_crash_serializing_images(monkeypatch):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
    from django.core.asgi import get_asgi_application

    from app.api import room as room_api

    class FakeRoom:
        id = uuid4()
        landlord_id = uuid4()
        status = "PENDING"
        created_at = "2026-01-01T00:00:00Z"
        updated_at = "2026-01-01T00:00:00Z"
        title = "t"
        description = "d"
        monthly_price = 1
        deposit = 1
        electric_price = 1
        water_price = 1
        area = 1
        max_people = 1
        gender_preference = "ANY"
        available_date = "2026-01-01T00:00:00Z"
        province = "HCM"
        district = "D1"
        ward = "W1"
        full_address = "addr"
        latitude = None
        longitude = None
        amenities = {}
        rules = {}
        images = []

    class FakeRoomService:
        def __init__(self, _db):
            pass

        async def create_room(self, landlord_id, room_in):
            return FakeRoom()

    monkeypatch.setattr(room_api, "AsyncSessionLocal", lambda: DummySession())
    monkeypatch.setattr(room_api, "RoomService", FakeRoomService)

    token = create_access_token({"sub": str(uuid4()), "role": "LANDLORD"})
    app = get_asgi_application()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/rooms/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Phòng trọ",
                "description": "desc",
                "monthly_price": 1,
                "deposit": 1,
                "electric_price": 1,
                "water_price": 1,
                "area": 1,
                "max_people": 1,
                "gender_preference": "ANY",
                "available_date": "2026-01-01T00:00:00Z",
                "province": "HCM",
                "district": "D1",
                "ward": "W1",
                "full_address": "addr",
                "latitude": 1.0,
                "longitude": 1.0,
                "amenities": {},
                "rules": {},
                "image_urls": [],
            },
        )

    assert resp.status_code in (200, 201)

