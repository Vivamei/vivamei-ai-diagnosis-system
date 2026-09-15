import pytest

from app.deps.redis import get_redis
from app.services.sse_buffer import SseBuffer


@pytest.mark.asyncio
async def test_push_and_read_from_start():
    async for r in get_redis():
        buf = SseBuffer(r, task_id="ttest_a")
        await buf.delete()
        await buf.push("phase", '{"phase":"stype"}')
        await buf.push("delta", '{"text":"hi"}')
        events = [e async for e in buf.replay(last_id=None)]
        assert len(events) == 2
        assert events[0][1] == "phase"
        assert events[1][1] == "delta"
        await buf.delete()
        break


@pytest.mark.asyncio
async def test_replay_after_last_event_id():
    async for r in get_redis():
        buf = SseBuffer(r, task_id="ttest_b")
        await buf.delete()
        await buf.push("phase", "{}")
        eid = await buf.last_id()
        await buf.push("delta", "{}")
        evs = [e async for e in buf.replay(last_id=eid)]
        assert len(evs) == 1
        assert evs[0][1] == "delta"
        await buf.delete()
        break
