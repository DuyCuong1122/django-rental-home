import asyncio
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone


BASE = "http://localhost:8000"


def post(path: str, data: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{path} -> {e.code} {e.read().decode()}")


async def main() -> None:
    suffix = str(int(time.time()))
    password = "Password123!"

    landlord = post(
        "/api/v1/auth/register",
        {
            "email": f"landlord_push_{suffix}@example.com",
            "role": "LANDLORD",
            "password": password,
            "full_name": "Landlord Push",
            "phone": "0900000003",
        },
    )
    landlord_token = landlord["token"]["access_token"]

    tenant = post(
        "/api/v1/auth/register",
        {
            "email": f"tenant_push_{suffix}@example.com",
            "role": "TENANT",
            "password": password,
            "full_name": "Tenant Push",
            "phone": "0900000004",
        },
    )
    tenant_token = tenant["token"]["access_token"]

    post("/api/v1/users/fcm-token", {"token": "dummy_fcm_token", "platform": "android"}, token=landlord_token)

    now = datetime.now(timezone.utc).isoformat()
    room = post(
        "/api/v1/rooms/",
        {
            "title": "Room Push",
            "description": "Desc",
            "monthly_price": 100.0,
            "deposit": 50.0,
            "electric_price": 3.0,
            "water_price": 2.0,
            "area": 20.0,
            "max_people": 2,
            "gender_preference": "ANY",
            "available_date": now,
            "province": "HCM",
            "district": "D1",
            "ward": "W1",
            "full_address": "Addr",
            "amenities": {},
            "rules": {},
            "image_urls": [],
        },
        token=landlord_token,
    )
    room_id = room["id"]

    chat_room = post("/api/v1/chat/rooms", {"room_id": room_id}, token=tenant_token)
    chat_room_id = chat_room["chat_room"]["id"]

    import websockets

    ws_url = f"ws://localhost:8000/ws/chat/{chat_room_id}/?token={tenant_token}"
    async with websockets.connect(ws_url) as ws:
        await ws.send(
            json.dumps(
                {
                    "type": "send_message",
                    "temp_id": "46bb90b0-e792-4d9b-aa85-8bd2ee35c000",
                    "message_type": "TEXT",
                    "content": "hello-push",
                }
            )
        )
        await ws.recv()


if __name__ == "__main__":
    asyncio.run(main())

