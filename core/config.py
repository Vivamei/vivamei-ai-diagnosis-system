"""
core/config.py

Centralized, type-safe configuration using pydantic-settings.
Replaces global module-level variables with a proper Settings class.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM Provider ──────────────────────────────────────────
    llm_provider: str = "mock"

    # Alibaba DashScope / Qwen
    dashscope_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-vl-max"

    # Volcengine Ark / Doubao
    ark_api_key: str = ""
    ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    ark_model: str = ""

    # Public base URL for image serving (e.g., ngrok tunnel)
    public_base_url: str = ""
    # ── Alibaba Cloud OSS ─────────────────────────────────────
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_ENDPOINT: str = ""
    OSS_BUCKET_NAME: str = ""
    # ── Server ────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000

    # ── Queue / concurrency ──────────────────────────────────
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"
    queue_user_requests_per_minute: int = 5
    queue_user_max_active_jobs: int = 5
    queue_ip_requests_per_minute: int = 300
    queue_ip_max_active_jobs: int = 300
    queue_global_max_queued_jobs: int = 500
    queue_global_max_inflight: int = 10
    queue_job_ttl_seconds: int = 86400
    queue_execution_lease_seconds: int = 600
    trust_proxy_headers: bool = False
    trusted_proxy_ips: str = ""

    # ── App Metadata ──────────────────────────────────────────
    app_name: str = "AI 4S 美学顾问"
    app_version: str = "2.0.0"
    app_description: str = "企业级 4S 美学评估系统"

    # ── Computed Properties ───────────────────────────────────
    @property
    def is_mock(self) -> bool:
        return self.llm_provider.lower().strip() == "mock"

    @property
    def is_qwen(self) -> bool:
        return self.llm_provider.lower().strip() == "qwen"

    @property
    def is_volcengine(self) -> bool:
        return self.llm_provider.lower().strip() == "volcengine"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings instance."""
    return Settings()
