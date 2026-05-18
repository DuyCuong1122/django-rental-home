from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate
from app.schemas.auth import LoginRequest, LoginResponse, Token
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.core.redis import get_redis

class AuthService:
    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)

    async def register(self, user_in: UserCreate):
        existing_user = await self.user_repo.get_by_email(user_in.email)
        if existing_user:
            raise ValueError("Email already registered")
        
        user = await self.user_repo.create_user(user_in)
        access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        return LoginResponse(
            token=Token(access_token=access_token, refresh_token=refresh_token),
            user=user
        )

    async def login(self, login_data: LoginRequest):
        user = await self.user_repo.get_by_email(login_data.email)
        if not user or not verify_password(login_data.password, user.password_hash):
            raise ValueError("Incorrect email or password")
        
        if not user.is_active:
            raise ValueError("Inactive user")
            
        access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        return LoginResponse(
            token=Token(access_token=access_token, refresh_token=refresh_token),
            user=user
        )

    async def logout(self, refresh_token: str):
        redis = await get_redis()
        try:
            payload = decode_token(refresh_token)
            jti = payload.get("exp") # simple proxy for uniqueness, or use a proper jti
            # In a real app, you would extract JTI from token. 
            await redis.setex(f"jwt:blacklist:{refresh_token}", 604800, "true")
        except Exception:
            pass

    async def refresh(self, refresh_token: str):
        redis = await get_redis()
        is_blacklisted = await redis.get(f"jwt:blacklist:{refresh_token}")
        if is_blacklisted:
            raise ValueError("Token blacklisted")
            
        payload = decode_token(refresh_token)
        user_id = payload.get("sub")
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
            
        access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
        return {"access_token": access_token}
