from app.services.llm.factory import get_llm_provider
from app.services.llm.mock import MockLLMProvider


def test_factory_returns_mock_by_default(monkeypatch):
    # 重置单例
    import app.services.llm.factory as f
    f._instance = None
    monkeypatch.setattr(f.settings, "llm_provider", "mock")
    p = get_llm_provider()
    assert isinstance(p, MockLLMProvider)
