from ninja import Router
from ninja.errors import HttpError
from app.schemas.user import UserCreate
from app.schemas.auth import LoginRequest, LoginResponse, RefreshRequest, LogoutRequest
from app.services.auth import AuthService
from app.core.database import AsyncSessionLocal
from asgiref.sync import sync_to_async

auth_router = Router(tags=["Authentication"])

@auth_router.post("/register", response=LoginResponse)
async def register(request, payload: UserCreate):
    async with AsyncSessionLocal() as db:
        service = AuthService(db)
        try:
            return await service.register(payload)
        except ValueError as e:
            raise HttpError(400, str(e))

@auth_router.post("/login", response=LoginResponse)
async def login(request, payload: LoginRequest):
    async with AsyncSessionLocal() as db:
        service = AuthService(db)
        try:
            return await service.login(payload)
        except ValueError as e:
            raise HttpError(401, str(e))

@auth_router.post("/logout")
async def logout(request, payload: LogoutRequest):
    async with AsyncSessionLocal() as db:
        service = AuthService(db)
        await service.logout(payload.refresh_token)
        return {"success": True}

@auth_router.post("/refresh")
async def refresh(request, payload: RefreshRequest):
    async with AsyncSessionLocal() as db:
        service = AuthService(db)
        try:
            return await service.refresh(payload.refresh_token)
        except ValueError as e:
            raise HttpError(401, str(e))
