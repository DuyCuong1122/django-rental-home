from typing import Annotated

from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator
from uuid import UUID
from datetime import datetime

class ProfileBase(BaseModel):
    full_name: str
    phone: str | None = None
    avatar_url: str | None = None
    bio: str | None = None

class ProfileResponse(ProfileBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class UserBase(BaseModel):
    email: EmailStr
    role: str

class UserCreate(UserBase):
    password: Annotated[str, Field(min_length=8, max_length=256)]
    full_name: str
    phone: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password_bytes_length(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 1024:
            raise ValueError("Mật khẩu quá dài (tối đa 1024 bytes).")
        return v

class UserResponse(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime
    profile: ProfileResponse | None = None
    
    model_config = ConfigDict(from_attributes=True)
