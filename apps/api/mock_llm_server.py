"""Standalone mock LLM HTTP server for local development.

模拟同事 LLM 服务的 `POST /v1/analyze` SSE 接口（契约见 docs/LLM_API_ALIGNMENT.md §1）。
复用 mock/sample_report.json，与进程内 MockLLMProvider 行为一致，但走真实
HTTP/SSE 链路，可用于联调 QwenLLMProvider。

用法：
    cd apps/api && poetry run python mock_llm_server.py [--port 9000] [--frame-delay 1.0]

切换 API 走这个 mock：
    在 .env / 启动环境里设
        LLM_PROVIDER=qwen
        LLM_QWEN_BASE_URL=http://localhost:9000

可选场景测试（请求里带 user_hints 触发）：
    {"userHints": {"scenario": "slow"}}     -> phase 间隔 ×3
    {"userHints": {"scenario": "error"}}    -> 第二个 phase 后吐 error
    {"userHints": {"scenario": "banned"}}   -> delta 注入敏感词（验证审核拦截）
"""
import argparse
import asyncio
import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

FIXTURE = Path(__file__).resolve().parents[2] / "mock" / "sample_report.json"

app = FastAPI(title="venus-4s mock LLM service")
_data = json.loads(FIXTURE.read_text(encoding="utf-8"))

FRAME_DELAY = 1.0  # 由 CLI --frame-delay 覆盖


def _sse(event: dict) -> bytes:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")


async def _event_stream(body: dict, request: Request):
    hints = (body.get("userHints") or {}) if isinstance(body, dict) else {}
    scenario = hints.get("scenario")
    delay = FRAME_DELAY * (3 if scenario == "slow" else 1)

    labels = {
        "stype": "分相分析中",
        "style": "分型分析中",
        "subzone": "分区分析中",
        "struct": "分层分析中",
    }
    phases = ("stype", "style", "subzone", "struct")

    for idx, phase in enumerate(phases):
        if await request.is_disconnected():
            return
        yield _sse({"type": "phase", "phase": phase, "payload": {"label": labels[phase]}})
        await asyncio.sleep(delay)

        text = _data[phase].get("narrative", "")
        if scenario == "banned" and phase == "style":
            text += "（建议进行医疗治疗以保证效果）"  # 触发本方 sensitive_words
        chunk = 12
        for i in range(0, len(text), chunk):
            if await request.is_disconnected():
                return
            yield _sse({"type": "delta", "phase": phase, "text": text[i : i + chunk]})
            await asyncio.sleep(delay * 0.2)

        yield _sse({"type": "phase_done", "phase": phase, "payload": _data[phase]})

        if scenario == "error" and idx == 1:
            yield _sse({
                "type": "error",
                "error": {"code": "LLM_TIMEOUT", "message": "模拟超时", "retryable": True},
            })
            return

    yield _sse({"type": "radar", "radar": _data["radar"]})
    yield _sse({"type": "done", "payload": {"optimization": _data["optimization"]}})


@app.post("/v1/analyze")
async def analyze(req: Request):
    body = await req.json()
    task_id = body.get("taskId")
    image_url = body.get("imageUrl", "")
    if len(image_url) > 80:
        image_url = image_url[:77] + "..."
    print(f"[mock-llm] /v1/analyze taskId={task_id!r} imageUrl={image_url!r}")
    return StreamingResponse(
        _event_stream(body, req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/health")
def health():
    return {"ok": True, "fixture": FIXTURE.name, "frame_delay": FRAME_DELAY}


def main():
    global FRAME_DELAY
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=9000)
    p.add_argument(
        "--frame-delay",
        type=float,
        default=1.0,
        help="phase 间隔秒数；自动化测试时可设 0 全速跑",
    )
    args = p.parse_args()
    FRAME_DELAY = args.frame_delay
    print(f"[mock-llm] listening on http://0.0.0.0:{args.port} (frame_delay={FRAME_DELAY}s)")
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
