from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import List, Dict, Any

class RoomImageSchema(BaseModel):
    id: UUID
    image_url: str
    sort_order: int
    
    model_config = ConfigDict(from_attributes=True)

class RoomBase(BaseModel):
    title: str
    description: str
    monthly_price: float
    deposit: float
    electric_price: float
    water_price: float
    area: float
    max_people: int
    gender_preference: str
    available_date: datetime
    province: str
    district: str
    ward: str
    full_address: str
    latitude: float | None = None
    longitude: float | None = None
    amenities: Dict[str, Any]
    rules: Dict[str, Any]

class RoomCreate(RoomBase):
    image_urls: List[str] = []

class RoomResponse(RoomBase):
    id: UUID
    landlord_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    images: List[RoomImageSchema] = []
    
    model_config = ConfigDict(from_attributes=True)

class RoomDetailResponse(RoomResponse):
    view_count: int = 0
    favorite_count: int = 0
    
class SearchQuery(BaseModel):
    keyword: str | None = None
    district: str | None = None
    ward: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    min_area: float | None = None
    max_area: float | None = None
    limit: int = 20
    offset: int = 0
