from typing import AsyncIterator

from redis.asyncio import Redis


class SseBuffer:
    """每 task 一个 Redis Stream，做 SSE 事件缓冲 + Last-Event-ID 续传。

    push: 写一帧；自动设 TTL
    replay: 从 last_id 之后回放（Last-Event-ID 为 None 时全量）
    """

    TTL = 1800  # 30 min

    def __init__(self, redis: Redis, task_id: str):
        self.redis = redis
        self.key = f"task:stream:{task_id}"

    async def push(self, event: str, data: str) -> str:
        msg_id = await self.redis.xadd(self.key, {"event": event, "data": data})
        await self.redis.expire(self.key, self.TTL)
        return msg_id.decode() if isinstance(msg_id, bytes) else msg_id

    async def last_id(self) -> str | None:
        info = await self.redis.xrevrange(self.key, count=1)
        if not info:
            return None
        return info[0][0].decode()

    async def replay(self, last_id: str | None) -> AsyncIterator[tuple[str, str, str]]:
        """yield (msg_id, event, data)。last_id=None 表示从头读。

        Redis 6.2+ 支持 ( 前缀做开区间起始。
        """
        rng_start = f"({last_id}" if last_id else "0"
        entries = await self.redis.xrange(self.key, min=rng_start, max="+")
        for mid, fields in entries:
            yield (
                mid.decode(),
                fields[b"event"].decode(),
                fields[b"data"].decode(),
            )

    async def delete(self) -> None:
        await self.redis.delete(self.key)
