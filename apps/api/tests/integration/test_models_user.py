from datetime import datetime

import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import User
from tests.helpers import make_phone_hash


@pytest.mark.asyncio
async def test_insert_user():
    async with SessionLocal() as s:
        u = User(
            phone="ciphertext_xx",
            phone_hash=make_phone_hash("models-user"),
            consent_at=datetime.utcnow(),
            consent_ver="v1.0",
        )
        s.add(u)
        await s.commit()
        await s.refresh(u)
        assert u.id is not None

        stmt = select(User).where(User.phone_hash == make_phone_hash("models-user"))
        got = (await s.execute(stmt)).scalar_one()
        assert got.id == u.id

        await s.delete(got)
        await s.commit()
