import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import AppError
from app.main import app


# 注册一个临时路由抛 AppError，仅供本测试使用
@app.get("/_test/boom")
async def _boom():
    raise AppError(code="TEST_BOOM", message="boom!", status_code=418)


@pytest.mark.asyncio
async def test_error_envelope_shape():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get("/_test/boom")
    assert r.status_code == 418
    body = r.json()
    assert body["code"] == "TEST_BOOM"
    assert body["message"] == "boom!"
    assert "requestId" in body
    assert r.headers["x-request-id"] == body["requestId"]


@pytest.mark.asyncio
async def test_request_id_passthrough():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get("/health", headers={"x-request-id": "rid-fixed"})
    assert r.headers["x-request-id"] == "rid-fixed"
