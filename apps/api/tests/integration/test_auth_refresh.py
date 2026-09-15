from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import issue_refresh_token
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User
from tests.helpers import make_phone_hash


@pytest.mark.asyncio
async def test_refresh_returns_new_access():
    async with SessionLocal() as s:
        u = User(
            phone="x",
            phone_hash=make_phone_hash("auth-refresh"),
            consent_at=datetime.utcnow(),
            consent_ver="v1.0",
        )
        s.add(u)
        await s.commit()
        await s.refresh(u)
        uid = u.id

    rt = issue_refresh_token(uid)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/api/auth/refresh", json={"refreshToken": rt})
    assert r.status_code == 200
    assert r.json()["accessToken"]


@pytest.mark.asyncio
async def test_refresh_with_access_token_rejected():
    from app.core.security import issue_access_token

    at = issue_access_token(user_id=1)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/api/auth/refresh", json={"refreshToken": at})
    assert r.status_code == 401
