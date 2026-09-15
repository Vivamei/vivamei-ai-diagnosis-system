from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import issue_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User
from tests.helpers import make_phone_hash


@pytest.mark.asyncio
async def test_upload_token_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/api/upload/token", json={})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_upload_token_returns_credentials():
    async with SessionLocal() as s:
        u = User(
            phone="x",
            phone_hash=make_phone_hash("upload-token"),
            consent_at=datetime.utcnow(),
            consent_ver="v1.0",
        )
        s.add(u)
        await s.commit()
        await s.refresh(u)
    tok = issue_access_token(u.id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post(
            "/api/upload/token",
            json={},
            headers={"Authorization": f"Bearer {tok}"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["objectKey"].startswith("uploads/")
    assert body["maxBytes"] == 5_242_880
    assert body["accessKeyId"]
