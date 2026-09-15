import json
from typing import AsyncIterator

import httpx

from app.core.config import settings
from app.services.llm.base import LLMEvent, LLMProvider, LLMRequest


class QwenLLMProvider(LLMProvider):
    """与同事 LLM 服务的 SSE 客户端。

    协议：POST /v1/analyze，body 为 LLMRequest，响应为 text/event-stream。
    每个 SSE event 的 data 行是一个 LLMEvent JSON。
    """

    name = "qwen-vl"

    def __init__(
        self,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._base = base_url or settings.llm_qwen_base_url
        self._client = httpx.AsyncClient(
            transport=transport, timeout=settings.llm_timeout_seconds
        )

    async def analyze_stream(self, req: LLMRequest) -> AsyncIterator[LLMEvent]:
        payload = {
            "schemaVersion": req.schema_version,
            "taskId": req.task_id,
            "imageUrl": req.image_url,
            "locale": req.locale,
            "userHints": req.user_hints,
            "promptOverrides": req.prompt_overrides,
        }
        async with self._client.stream(
            "POST",
            f"{self._base}/v1/analyze",
            json=payload,
            headers={"Accept": "text/event-stream"},
        ) as r:
            r.raise_for_status()
            buf: list[str] = []
            async for line in r.aiter_lines():
                if line == "":
                    if buf:
                        raw = "\n".join(buf)
                        buf.clear()
                        try:
                            yield LLMEvent(**json.loads(raw))
                        except Exception:
                            yield LLMEvent(
                                type="error",
                                error={"code": "LLM_BAD_FRAME", "frame": raw[:200]},
                            )
                elif line.startswith("data:"):
                    buf.append(line[5:].lstrip())
                # 其他行（event: / id: / : 注释）忽略——type 字段在 data JSON 中
