import asyncio
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import issue_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.photo import ModerationStatus, Photo
from app.models.user import User
from tests.helpers import make_phone_hash


@pytest.mark.asyncio
async def test_post_photo_registers_and_moderates():
    async with SessionLocal() as s:
        u = User(
            phone="x",
            phone_hash=make_phone_hash("photos-post"),
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
            "/api/photos",
            json={
                "ossKey": "uploads/2026/06/29/ok.jpg",
                "width": 1080,
                "height": 1440,
                "bytes": 800_000,
            },
            headers={"Authorization": f"Bearer {tok}"},
        )
    assert r.status_code == 200
    pid = r.json()["photoId"]

    # 后台 task 跑完
    await asyncio.sleep(0.5)
    async with SessionLocal() as s:
        p = (await s.execute(select(Photo).where(Photo.id == pid))).scalar_one()
        assert p.moderation_status == ModerationStatus.passed
