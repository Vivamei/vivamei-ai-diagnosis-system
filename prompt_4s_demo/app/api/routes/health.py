"""
app/api/routes/health.py

Health check and root endpoints.
"""

from fastapi import APIRouter

from core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/")
def root():
    """Service root."""
    settings = get_settings()
    return {
        "message": f"{settings.app_name} 已启动。",
        "provider": settings.llm_provider,
        "version": settings.app_version,
        "docs": "/docs",
    }


@router.get("/health")
def health():
    """Health check."""
    settings = get_settings()
    return {"status": "ok", "provider": settings.llm_provider}
