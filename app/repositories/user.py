from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import Optional
from app.models.user import User, Profile
from app.schemas.user import UserCreate
from app.core.security import get_password_hash

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).options(selectinload(User.profile)).where(User.email == email, User.is_deleted == False)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, user_id: str) -> Optional[User]:
        stmt = select(User).options(selectinload(User.profile)).where(User.id == user_id, User.is_deleted == False)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_user(self, user_in: UserCreate) -> User:
        db_user = User(
            email=user_in.email,
            password_hash=get_password_hash(user_in.password),
            role=user_in.role
        )
        self.session.add(db_user)
        await self.session.flush() # flush to get user id

        db_profile = Profile(
            user_id=db_user.id,
            full_name=user_in.full_name,
            phone=user_in.phone
        )
        self.session.add(db_profile)
        await self.session.commit()
        stmt = (
            select(User)
            .options(selectinload(User.profile))
            .where(User.id == db_user.id, User.is_deleted == False)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
