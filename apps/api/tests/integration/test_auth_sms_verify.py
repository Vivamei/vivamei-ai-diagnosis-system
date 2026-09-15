import pytest
from httpx import ASGITransport, AsyncClient

from app.deps.redis import get_redis
from app.main import app
from app.services.phone_crypto import hash_phone


@pytest.mark.asyncio
async def test_verify_happy_path():
    phone = "13700137000"
    async for r in get_redis():
        await r.setex(f"sms:code:{hash_phone(phone)}", 300, "654321")
        break
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post(
            "/api/auth/sms/verify",
            json={"phone": phone, "code": "654321", "consentVer": "v1.0"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["accessToken"] and body["refreshToken"]
    assert body["user"]["id"] > 0


@pytest.mark.asyncio
async def test_verify_bad_code():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post(
            "/api/auth/sms/verify",
            json={"phone": "13711111111", "code": "000000", "consentVer": "v1.0"},
        )
    assert r.status_code == 400
    assert r.json()["code"] == "AUTH_SMS_INVALID"
