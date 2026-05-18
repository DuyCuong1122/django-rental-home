from ninja import Router
from ninja.errors import HttpError
from app.schemas.appointment import AppointmentCreate, AppointmentUpdateStatus, AppointmentResponse
from app.api.deps import JWTAuth
from app.core.database import AsyncSessionLocal
from app.models.appointment import Appointment
from app.models.room import Room
from sqlalchemy.future import select
from uuid import UUID
from app.workers.notifications import send_push_notification

appointment_router = Router(tags=["Appointments"], auth=JWTAuth())

@appointment_router.post("/", response={201: AppointmentResponse})
async def create_appointment(request, payload: AppointmentCreate):
    tenant_id = UUID(request.auth.get("sub"))
    async with AsyncSessionLocal() as db:
        # Check room
        room_stmt = select(Room).where(Room.id == payload.room_id)
        result = await db.execute(room_stmt)
        room = result.scalars().first()
        if not room:
            raise HttpError(404, "Room not found")
            
        appointment = Appointment(
            tenant_id=tenant_id,
            landlord_id=room.landlord_id,
            room_id=payload.room_id,
            scheduled_time=payload.scheduled_time,
            note=payload.note,
            status="PENDING"
        )
        db.add(appointment)
        await db.commit()
        await db.refresh(appointment)
        
        # Async Push Notification via Celery
        send_push_notification.delay(
            str(room.landlord_id), 
            "New Appointment Request", 
            f"A tenant wants to view {room.title}"
        )
        
        return 201, appointment

@appointment_router.put("/{appointment_id}/status", response=AppointmentResponse)
async def update_appointment_status(request, appointment_id: UUID, payload: AppointmentUpdateStatus):
    user_id = UUID(request.auth.get("sub"))
    async with AsyncSessionLocal() as db:
        stmt = select(Appointment).where(Appointment.id == appointment_id)
        result = await db.execute(stmt)
        appointment = result.scalars().first()
        
        if not appointment:
            raise HttpError(404, "Appointment not found")
            
        if appointment.landlord_id != user_id:
            raise HttpError(403, "Only the landlord can update this appointment")
            
        if payload.status not in ["ACCEPTED", "REJECTED", "DONE"]:
            raise HttpError(400, "Invalid status")
            
        appointment.status = payload.status
        await db.commit()
        await db.refresh(appointment)
        
        # Async Push Notification via Celery
        send_push_notification.delay(
            str(appointment.tenant_id), 
            "Appointment Status Updated", 
            f"Your appointment has been {payload.status.lower()}"
        )
        
        return appointment
