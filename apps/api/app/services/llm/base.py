from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Literal

from pydantic import BaseModel


class LLMRequest(BaseModel):
    """对外稳定的 LLM 请求契约（v1）。

    扩展点：
    - user_hints: 8 万版/10 万版传更多上下文（如年龄段、肤况）
    - prompt_overrides: 临时改 prompt 用于灰度/AB 实验
    """

    schema_version: Literal["v1"] = "v1"
    task_id: str
    # 配了 OSS 时走 image_url（贵方从 OSS 拉图）；没配 OSS 时走本地 file 上传，
    # 由 image_bytes/image_mime 携带原图字节，provider 以 multipart 上送 /api/analyze-file。
    image_url: str = ""
    image_bytes: bytes | None = None
    image_mime: str | None = None
    locale: str = "zh-CN"
    user_id: int | None = None
    user_hints: dict[str, Any] | None = None
    prompt_overrides: dict[str, Any] | None = None


class LLMEvent(BaseModel):
    """LLM 流式事件，与 SSE event 1:1 对应但与 HTTP 解耦（方便单测、方便换协议）。"""

    type: Literal["phase", "delta", "phase_done", "radar", "done", "error"]
    phase: Literal["stype", "style", "subzone", "struct"] | None = None
    text: str | None = None
    payload: dict[str, Any] | None = None
    radar: dict[str, int] | None = None
    error: dict[str, Any] | None = None


class LLMProvider(ABC):
    """LLM 提供商抽象。dev/test 用 Mock，prod 用 Qwen。"""

    name: str

    @abstractmethod
    def analyze_stream(self, req: LLMRequest) -> AsyncIterator[LLMEvent]: ...
