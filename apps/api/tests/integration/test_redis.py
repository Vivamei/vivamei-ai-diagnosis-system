import pytest

from app.deps.redis import get_redis


@pytest.mark.asyncio
async def test_redis_ping():
    async for r in get_redis():
        assert await r.ping() is True
        await r.set("test:k", "v", ex=5)
        assert (await r.get("test:k")).decode() == "v"
        await r.delete("test:k")
        break
