"""
app/api/routes/analysis.py

Analysis API endpoints.
Thin layer — delegates all business logic to AnalysisService.
"""

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.api.dependencies import get_analysis_service
from core.exceptions import (
    AppException,
    ConfigurationError,
    ImageQualityError,
    LLMCallError,
    SafetyCheckError,
)
from schemas.requests import AnalyzeUrlRequest

router = APIRouter(prefix="/api", tags=["analysis"])
logger = logging.getLogger(__name__)


@router.post("/analyze-file")
async def analyze_file(
    file: UploadFile = File(..., description="用户上传的人脸照片"),
    user_id: Optional[str] = Form(default=None, description="可选用户 ID"),
):
    """Upload an image and generate a 4S aesthetic report."""
    try:
        service = get_analysis_service()
        return service.analyze_file(file, user_id=user_id)
    except ImageQualityError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "image_quality": exc.details,
            },
        )
    except (ConfigurationError, LLMCallError) as exc:
        logger.error("Analysis failed: %s", exc.message, exc_info=True)
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": exc.message},
        )
    except SafetyCheckError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "safety": {"hit_words": exc.hit_words},
            },
        )


@router.post("/analyze-url")
async def analyze_url(req: AnalyzeUrlRequest):
    """Analyze an image via public URL and generate a 4S aesthetic report."""
    if not req.image_url.startswith(("http://", "https://")):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "image_url 必须是公网可访问的 http/https 地址。",
            },
        )

    try:
        service = get_analysis_service()
        return service.analyze_url(req.image_url, user_id=req.user_id)
    except (ConfigurationError, LLMCallError) as exc:
        logger.error("Analysis failed: %s", exc.message, exc_info=True)
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": exc.message},
        )
    except SafetyCheckError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "safety": {"hit_words": exc.hit_words},
            },
        )
