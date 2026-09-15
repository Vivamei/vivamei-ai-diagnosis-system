from datetime import datetime

from pydantic import BaseModel, Field


class BookingCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    storeCode: str | None = None
    appointmentAt: datetime | None = None
    taskId: str | None = None
    remark: str | None = Field(default=None, max_length=255)
    source: str | None = None


class BookingCreateResponse(BaseModel):
    bookingId: int
