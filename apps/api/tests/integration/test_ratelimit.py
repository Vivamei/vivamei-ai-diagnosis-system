import asyncio

import pytest

from app.deps.redis import get_redis
from app.services.ratelimit import RateLimiter


@pytest.mark.asyncio
async def test_allows_within_limit():
    async for r in get_redis():
        rl = RateLimiter(r, "test:rl:a", limit=3, window_seconds=10)
        for _ in range(3):
            assert await rl.allow() is True
        assert await rl.allow() is False
        await r.delete("test:rl:a")
        break


@pytest.mark.asyncio
async def test_window_resets():
    async for r in get_redis():
        rl = RateLimiter(r, "test:rl:b", limit=1, window_seconds=1)
        assert await rl.allow() is True
        assert await rl.allow() is False
        await asyncio.sleep(1.2)
        assert await rl.allow() is True
        await r.delete("test:rl:b")
        break
