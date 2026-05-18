from ninja import Router
from ninja.errors import HttpError
from app.schemas.user import UserResponse, ProfileBase
from app.api.deps import JWTAuth
from app.repositories.user import UserRepository
from app.core.database import AsyncSessionLocal

profile_router = Router(tags=["Profile"], auth=JWTAuth())

@profile_router.get("/me", response=UserResponse)
async def get_me(request):
    user_id = request.auth.get("sub")
    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)
        if not user:
            raise HttpError(404, "User not found")
        return user

@profile_router.put("/me", response=UserResponse)
async def update_me(request, payload: ProfileBase):
    user_id = request.auth.get("sub")
    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)
        if not user:
            raise HttpError(404, "User not found")
        
        user.profile.full_name = payload.full_name
        user.profile.phone = payload.phone
        user.profile.bio = payload.bio
        user.profile.avatar_url = payload.avatar_url
        await db.commit()
        await db.refresh(user)
        return user
