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


class SaveFcmTokenRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    platform: str = Field(min_length=1, max_length=32)


class PushTestRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=512)
    data: dict[str, str] = Field(default_factory=dict)
    receiver_id: UUID | None = None


class PushTestResponse(BaseModel):
    success: bool = True
    receiver_id: UUID
    has_token: bool = True
    disabled: bool = False
    success_count: int = 0
    failure_count: int = 0
