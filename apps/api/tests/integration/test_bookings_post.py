from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import issue_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User
from tests.helpers import make_phone_hash


@pytest.mark.asyncio
async def test_create_booking():
    async with SessionLocal() as s:
        u = User(
            phone="x",
            phone_hash=make_phone_hash("bookings-create"),
            consent_at=datetime.utcnow(),
            consent_ver="v1.0",
        )
        s.add(u)
        await s.commit()
        await s.refresh(u)
        uid = u.id

    tok = issue_access_token(uid)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post(
            "/api/bookings",
            headers={"Authorization": f"Bearer {tok}"},
            json={
                "name": "张三",
                "phone": "13800138000",
                "storeCode": "SH01",
                "appointmentAt": "2026-07-02T14:00:00+08:00",
                "source": "qr",
            },
        )
    assert r.status_code == 201
    assert r.json()["bookingId"] > 0


@pytest.mark.asyncio
async def test_booking_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/api/bookings", json={"name": "x", "phone": "13800138000"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_booking_invalid_phone():
    async with SessionLocal() as s:
        u = User(
            phone="x",
            phone_hash=make_phone_hash("bookings-invalid-phone"),
            consent_at=datetime.utcnow(),
            consent_ver="v1.0",
        )
        s.add(u)
        await s.commit()
        await s.refresh(u)
    tok = issue_access_token(u.id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post(
            "/api/bookings",
            headers={"Authorization": f"Bearer {tok}"},
            json={"name": "x", "phone": "not-a-phone"},
        )
    assert r.status_code == 422  # Pydantic validation
