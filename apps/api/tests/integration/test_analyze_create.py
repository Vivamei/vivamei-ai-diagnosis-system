from datetime import datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select  # noqa: F401  (kept for symmetry across tests)

from app.core.security import issue_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.photo import ModerationStatus, Photo
from app.models.user import User
from tests.helpers import TEST_OSS_KEY, make_phone_hash


async def _make_user_and_photo(
    status: ModerationStatus = ModerationStatus.passed,
    phone_hash: str = make_phone_hash("analyze-create-default"),
):
    async with SessionLocal() as s:
        u = User(
            phone="x",
            phone_hash=phone_hash,
            consent_at=datetime.utcnow(),
            consent_ver="v1.0",
        )
        s.add(u)
        await s.commit()
        await s.refresh(u)
        p = Photo(
            user_id=u.id,
            oss_key=TEST_OSS_KEY,
            moderation_status=status,
            expires_at=datetime.utcnow() + timedelta(days=10),
        )
        s.add(p)
        await s.commit()
        await s.refresh(p)
        return u, p


@pytest.mark.asyncio
async def test_analyze_creates_task():
    u, p = await _make_user_and_photo(phone_hash=make_phone_hash("analyze-create-happy"))
    tok = issue_access_token(u.id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post(
            "/api/analyze",
            json={"photoId": p.id},
            headers={"Authorization": f"Bearer {tok}"},
        )
    assert r.status_code == 202
    body = r.json()
    assert len(body["taskId"]) == 26
    assert body["status"] == "queued"


@pytest.mark.asyncio
async def test_analyze_rejects_when_photo_moderation_failed():
    u, p = await _make_user_and_photo(
        status=ModerationStatus.rejected, phone_hash=make_phone_hash("analyze-create-rejected")
    )
    tok = issue_access_token(u.id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post(
            "/api/analyze",
            json={"photoId": p.id},
            headers={"Authorization": f"Bearer {tok}"},
        )
    assert r.status_code == 422
    assert r.json()["code"] == "PHOTO_MODERATION_REJECTED"
