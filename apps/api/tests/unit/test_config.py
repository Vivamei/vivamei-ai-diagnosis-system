from app.core.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql+aiomysql://u:p@h/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("PHONE_DEK_BASE64", "A" * 44)
    monkeypatch.setenv("PHONE_HMAC_KEY", "h" * 32)
    # _env_file=None 关掉 dotenv 加载：默认会读 config/dev.env，那里的 LLM_PROVIDER 等
    # 真实配置会盖掉代码里的默认值，本用例断言的恰恰是「不配任何东西时的默认值」。
    s = Settings(_env_file=None)
    assert s.database_url.startswith("mysql+aiomysql://")
    assert s.jwt_access_ttl_seconds == 3600  # default
    assert s.llm_provider == "mock"  # default
