from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/api/config")
async def public_config():
    """前端公开配置（无需登录）。分析页文案与预计等待时长走这里，改 .env 即生效。"""
    hints = [h for h in settings.analyze_wait_hints.split("|") if h.strip()]
    return {
        "analyzeEtaSeconds": settings.analyze_eta_seconds,
        "analyzeTitlePreparing": settings.analyze_title_preparing,
        "analyzeTitleAnalyzing": settings.analyze_title_analyzing,
        "analyzeSubtitle": settings.analyze_subtitle,
        "analyzeWaitHints": hints,
        "analyzeWaitNote": settings.analyze_wait_note,
    }
