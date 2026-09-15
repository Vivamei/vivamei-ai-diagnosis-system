from dataclasses import dataclass

from redis.asyncio import Redis


@dataclass
class RateLimiter:
    """简化的固定窗口计数器：INCR + 首次 EXPIRE。够用于 MVP。"""

    redis: Redis
    key: str
    limit: int
    window_seconds: int

    async def allow(self) -> bool:
        async with self.redis.pipeline(transaction=True) as p:
            p.incr(self.key)
            p.expire(self.key, self.window_seconds, nx=True)
            count, _ = await p.execute()
        return int(count) <= self.limit

    async def peek(self) -> int:
        """只读当前窗口计数，不递增（用于前置提示，不消耗配额）。"""
        v = await self.redis.get(self.key)
        return int(v) if v else 0
