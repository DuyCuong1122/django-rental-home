import pytest
from httpx import AsyncClient
from app.asgi import application

@pytest.mark.asyncio
async def test_health_check():
    # Because we're using Django ASGI, we can test it using httpx ASGITransport
    from httpx import ASGITransport
    
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
