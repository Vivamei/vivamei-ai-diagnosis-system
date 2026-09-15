import asyncio
import json
from pathlib import Path
from typing import AsyncIterator

from app.services.llm.base import LLMEvent, LLMProvider, LLMRequest

_parents = Path(__file__).resolve().parents
_FIXTURE = (
    (_parents[5] if len(_parents) > 5 else _parents[-1]) / "mock" / "sample_report.json"
)


class MockLLMProvider(LLMProvider):
    """本地 mock：按目标时长逐字段吐 phase/delta/phase_done/radar/done。

    - `frame_delay=1.0`（默认）：单个 phase 约 6s（用户体验目标 5–10s）
    - `frame_delay=0`（测试）：全部瞬时完成
    - 其他值：与默认成比例缩放（例如 2.0 → 每个 phase ≈ 12s）
    """

    name = "mock"

    def __init__(self, frame_delay: float = 1.0):
        self.frame_delay = frame_delay
        self._data = json.loads(_FIXTURE.read_text(encoding="utf-8"))

    async def analyze_stream(self, req: LLMRequest) -> AsyncIterator[LLMEvent]:
        labels = {
            "stype": "分相分析中",
            "style": "分型分析中",
            "subzone": "分区分析中",
            "struct": "分层分析中",
        }
        phase_seconds = 6.0 * self.frame_delay
        settle = min(0.9, phase_seconds * 0.15)

        for phase in ("style", "stype", "subzone", "struct"):
            yield LLMEvent(type="phase", phase=phase, payload={"label": labels[phase]})
            if settle > 0:
                await asyncio.sleep(settle)

            src = self._data[phase]
            # narrative 缺失时依次 fallback，保证 subzone/struct 也有流式文字
            text = (
                src.get("narrative")
                or src.get("summary")
                or src.get("description")
                or ""
            )

            stream_budget = max(0.0, phase_seconds - settle)
            if text and stream_budget > 0:
                chunk_size = 6
                chunks = [
                    text[i : i + chunk_size] for i in range(0, len(text), chunk_size)
                ]
                per_chunk = stream_budget / len(chunks)
                for c in chunks:
                    yield LLMEvent(type="delta", phase=phase, text=c)
                    if per_chunk > 0:
                        await asyncio.sleep(per_chunk)
            elif stream_budget > 0:
                await asyncio.sleep(stream_budget)

            yield LLMEvent(type="phase_done", phase=phase, payload=src)

        yield LLMEvent(type="radar", radar=self._data["radar"])
        # extra 的字段与 QwenSyncLLMProvider 对齐，否则 mock 模式下报告页的
        # 雷达图数值、优化方向、CTA 等区块全是空的，跟真实环境对不上。
        chart = self._data.get("radar_chart") or {}
        keys = chart.get("keys") or ["stype", "style", "subzone", "struct"]
        yield LLMEvent(
            type="done",
            payload={
                "optimization": self._data["optimization"],
                "extra": {
                    "aesthetic_optimization": self._data.get("aesthetic_optimization"),
                    "project_directions": self._data.get("project_directions"),
                    "mapped_project_directions": self._data.get(
                        "mapped_project_directions"
                    ),
                    "lead_cta": self._data.get("lead_cta"),
                    "disclaimer": self._data.get("disclaimer"),
                    "radar_semantics": chart.get("semantics"),
                    "radar_max": chart.get("max"),
                    "state_values": dict(zip(keys, chart.get("state_values") or [])),
                },
            },
        )
