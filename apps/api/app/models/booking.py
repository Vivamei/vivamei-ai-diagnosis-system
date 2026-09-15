import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BookingStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    arrived = "arrived"
    closed = "closed"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False, index=True
    )
    task_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("analysis_tasks.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    # 同 users 表：加密存储 + HMAC
    phone: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    store_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    appointment_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus), nullable=False, default=BookingStatus.new, index=True
    )
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
