import pytest

from app.services.llm.base import LLMRequest
from app.services.llm.mock import MockLLMProvider


@pytest.mark.asyncio
async def test_mock_emits_full_lifecycle():
    p = MockLLMProvider(frame_delay=0)  # 测试期不等待
    events = []
    async for ev in p.analyze_stream(LLMRequest(task_id="t1", image_url="http://x")):
        events.append(ev)

    types = [e.type for e in events]
    assert types[0] == "phase"
    assert types[-1] == "done"
    assert types.count("phase") == 4
    assert types.count("phase_done") == 4
    assert "radar" in types

    # 校验四维 payload 齐全
    phase_dones = [e for e in events if e.type == "phase_done"]
    phases_done = {e.phase for e in phase_dones}
    assert phases_done == {"stype", "style", "subzone", "struct"}

    # radar 数据 0-100
    radar_ev = next(e for e in events if e.type == "radar")
    assert all(0 <= v <= 100 for v in radar_ev.radar.values())
