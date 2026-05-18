from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

class AppointmentBase(BaseModel):
    room_id: UUID
    scheduled_time: datetime
    note: str | None = None

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdateStatus(BaseModel):
    status: str

class AppointmentResponse(AppointmentBase):
    id: UUID
    tenant_id: UUID
    landlord_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
