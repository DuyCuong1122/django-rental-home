import os
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token


class DummySession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@dataclass
class FakeInboxItem:
    id: object
    participant: dict
    room: dict | None
    last_message: dict | None
    unread_count: int


@pytest.mark.asyncio
async def test_chat_create_room_requires_auth():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
    from django.core.asgi import get_asgi_application

    app = get_asgi_application()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/v1/chat/rooms", json={"room_id": str(uuid4())})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_chat_rooms_list_ok(monkeypatch):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
    from django.core.asgi import get_asgi_application

    from app.api import chat as chat_api

    async def fake_list_rooms(self, *, user_id, cursor, limit, filter):
        item = FakeInboxItem(
            id=uuid4(),
            participant={"id": str(uuid4()), "full_name": "Other", "avatar_url": None, "is_online": False},
            room=None,
            last_message=None,
            unread_count=0,
        )
        return {"data": [item.__dict__], "next_cursor": None}

    class FakeChatService:
        def __init__(self, _db):
            pass

        list_rooms = fake_list_rooms

    monkeypatch.setattr(chat_api, "AsyncSessionLocal", lambda: DummySession())
    monkeypatch.setattr(chat_api, "ChatService", FakeChatService)

    token = create_access_token({"sub": str(uuid4()), "role": "TENANT"})
    app = get_asgi_application()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/chat/rooms", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body


@pytest.mark.asyncio
async def test_chat_unread_count_ok(monkeypatch):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
    from django.core.asgi import get_asgi_application

    from app.api import chat as chat_api

    async def fake_total_unread_count(self, *, user_id):
        return 12

    class FakeChatService:
        def __init__(self, _db):
            pass

        total_unread_count = fake_total_unread_count

    monkeypatch.setattr(chat_api, "AsyncSessionLocal", lambda: DummySession())
    monkeypatch.setattr(chat_api, "ChatService", FakeChatService)

    token = create_access_token({"sub": str(uuid4()), "role": "TENANT"})
    app = get_asgi_application()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/chat/unread-count", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.json()["count"] == 12

