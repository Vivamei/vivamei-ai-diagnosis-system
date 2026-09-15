from fastapi import APIRouter, Depends, Request

from app.core.audit import write_audit
from app.deps.auth import CurrentUser, get_current_user
from app.deps.db import get_db
from app.models.booking import Booking
from app.schemas.booking import BookingCreateRequest, BookingCreateResponse
from app.services.phone_crypto import encrypt_phone, hash_phone

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.post("", response_model=BookingCreateResponse, status_code=201)
async def create_booking(
    req: BookingCreateRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    b = Booking(
        user_id=user.id,
        task_id=req.taskId,
        name=req.name,
        phone=encrypt_phone(req.phone),
        phone_hash=hash_phone(req.phone),
        store_code=req.storeCode,
        appointment_at=req.appointmentAt,
        remark=req.remark,
        source=req.source,
    )
    db.add(b)
    await db.commit()
    await db.refresh(b)
    await write_audit(
        "booking.create",
        actor_id=user.id,
        actor_ip=request.client.host if request.client else None,
        target_type="booking",
        target_id=str(b.id),
    )
    return BookingCreateResponse(bookingId=b.id)
