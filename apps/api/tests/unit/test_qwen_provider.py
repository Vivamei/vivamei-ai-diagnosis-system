import httpx
import pytest

from app.services.llm.base import LLMRequest
from app.services.llm.qwen import QwenLLMProvider


@pytest.mark.asyncio
async def test_qwen_parses_sse_stream():
    sse_body = (
        'event: phase\n'
        'data: {"type":"phase","phase":"stype"}\n\n'
        'event: delta\n'
        'data: {"type":"delta","phase":"stype","text":"骨相"}\n\n'
        'event: done\n'
        'data: {"type":"done"}\n\n'
    )

    async def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text=sse_body,
        )

    transport = httpx.MockTransport(handler)
    p = QwenLLMProvider(base_url="http://llm", transport=transport)
    events = [
        ev async for ev in p.analyze_stream(LLMRequest(task_id="t", image_url="http://x"))
    ]
    types = [e.type for e in events]
    assert types == ["phase", "delta", "done"]
    assert events[1].text == "骨相"
