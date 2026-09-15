from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import issue_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.user import User
from tests.helpers import make_phone_hash


@pytest.mark.asyncio
async def test_booking_writes_audit():
    async with SessionLocal() as s:
        u = User(
            phone="x",
            phone_hash=make_phone_hash("audit"),
            consent_at=datetime.utcnow(),
            consent_ver="v1.0",
        )
        s.add(u)
        await s.commit()
        await s.refresh(u)
        uid = u.id

    tok = issue_access_token(uid)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        await ac.post(
            "/api/bookings",
            headers={"Authorization": f"Bearer {tok}"},
            json={"name": "X", "phone": "13800138000"},
        )

    async with SessionLocal() as s:
        logs = (
            await s.execute(
                select(AuditLog).where(
                    AuditLog.action == "booking.create", AuditLog.actor_id == uid
                )
            )
        ).scalars().all()
        assert len(logs) >= 1
        assert logs[0].target_type == "booking"
