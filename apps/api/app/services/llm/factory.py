from app.core.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.mock import MockLLMProvider
from app.services.llm.qwen import QwenLLMProvider
from app.services.llm.qwen_sync import QwenSyncLLMProvider

_instance: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    """单例 Provider。配置 LLM_PROVIDER=mock|async|sync|queue。
      mock  —— 进程内 mock
      async —— 贵方 SSE 流式（QwenLLMProvider）
      sync  —— 贵方 /analyze-url 一次性返回（QwenSyncLLMProvider，不轮询）
      queue —— 贵方提交 + 轮询 /api/analysis-jobs/{job_id}（QwenSyncLLMProvider，轮询）

    取 llm_provider_effective 而非 llm_provider：ALLOW_MOCK 含 llm（或 APP_ENV=test）
    时恒为 mock，不用再把 LLM_PROVIDER 单独改一遍；没列进 ALLOW_MOCK 时
    LLM_PROVIDER 说了算，想指定 sync/queue/async 照填不误。
    """
    global _instance
    if _instance is None:
        provider = settings.llm_provider_effective
        if provider == "mock":
            _instance = MockLLMProvider()
        elif provider == "async":
            _instance = QwenLLMProvider()
        elif provider == "sync":
            _instance = QwenSyncLLMProvider(poll=False)
        elif provider == "queue":
            _instance = QwenSyncLLMProvider(poll=True)
        else:
            raise RuntimeError(f"unknown LLM_PROVIDER: {provider}")
    return _instance
