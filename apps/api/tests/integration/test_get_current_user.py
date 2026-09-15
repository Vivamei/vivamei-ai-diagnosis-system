import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient

from app.core.security import issue_access_token
from app.deps.auth import CurrentUser, get_current_user
from app.main import app


@app.get("/_test/me")
async def _me(u: CurrentUser = Depends(get_current_user)):
    return {"id": u.id}


@pytest.mark.asyncio
async def test_me_missing_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get("/_test/me")
    assert r.status_code == 401
    assert r.json()["code"] == "AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_me_invalid_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get("/_test/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401
    assert r.json()["code"] == "AUTH_INVALID_TOKEN"


@pytest.mark.asyncio
async def test_me_user_not_in_db():
    tok = issue_access_token(user_id=999_999_999)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get("/_test/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401
