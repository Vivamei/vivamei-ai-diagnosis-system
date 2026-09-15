"""
app/api/routes/analysis.py

Analysis API endpoints.
Thin layer — delegates all business logic to AnalysisService.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, Request, UploadFile, Query
from fastapi.responses import JSONResponse

from app.api.dependencies import get_analysis_service, get_job_queue
from core.client_ip import get_client_ip
from core.config import get_settings
from core.exceptions import (
    AppException,
    ConfigurationError,
    ImageQualityError,
    LLMCallError,
    SafetyCheckError,
)
from services.queueing import QueueAdmissionError
from schemas.requests import AnalyzeUrlRequest

router = APIRouter(prefix="/api", tags=["analysis"])
logger = logging.getLogger(__name__)


def error_response(exc: AppException) -> JSONResponse:
    """Serialize a stable machine-readable error while keeping legacy message."""
    request_id = exc.request_id or uuid.uuid4().hex
    exc.request_id = request_id
    headers = {}
    retry_after = exc.details.get("retry_after_seconds")
    if retry_after:
        headers["Retry-After"] = str(retry_after)
    error = {
        "code": exc.code,
        "message": exc.message,
        "retryable": exc.retryable,
        "request_id": request_id,
    }
    if exc.details:
        error["details"] = exc.details
    return JSONResponse(
        status_code=exc.status_code,
        headers=headers,
        content={
            "success": False,
            "error": error,
            "message": exc.message,
        },
    )


def queued_response(job: dict) -> JSONResponse:
    """Return a polling contract immediately after queue admission."""
    job_id = job["job_id"]
    return JSONResponse(
        status_code=202,
        content={
            "success": True,
            "status": "QUEUED",
            "job_id": job_id,
            "poll_url": f"/api/analysis-jobs/{job_id}",
            "message": "任务已进入分析队列，请轮询任务状态。",
        },
    )


@router.post("/analyze-file")
async def analyze_file(
    request: Request,
    file: UploadFile = File(..., description="用户上传的人脸照片"),
    user_id: Optional[str] = Form(default=None, description="用户 ID；queue 模式必填"),
    mode: str = Query(default="queue", description="分析模式：queue 排队模式，sync 同步模式，async 异步并行模式"),
):
    """Upload an image and generate a 4S aesthetic report."""
    try:
        if mode == "queue":
            job = get_job_queue().submit_file(
                file, user_id, get_client_ip(request, get_settings())
            )
            return queued_response(job)
        service = get_analysis_service()
        if mode == "async":
            return await service.analyze_file_async(file, user_id=user_id)
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
    except (ConfigurationError, LLMCallError, QueueAdmissionError) as exc:
        response = error_response(exc)
        logger.error(
            "Analysis failed code=%s retryable=%s request_id=%s",
            exc.code,
            exc.retryable,
            exc.request_id,
            exc_info=True,
        )
        return response
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
async def analyze_url(
    request: Request,
    req: AnalyzeUrlRequest,
    mode: str = Query(default="queue", description="分析模式：queue 排队模式，sync 同步模式，async 异步并行模式"),
):
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
        if mode == "queue":
            job = get_job_queue().submit_url(
                req.image_url, req.user_id, get_client_ip(request, get_settings())
            )
            return queued_response(job)
        service = get_analysis_service()
        if mode == "async":
            return await service.analyze_url_async(req.image_url, user_id=req.user_id)
        return service.analyze_url(req.image_url, user_id=req.user_id)
    except (ConfigurationError, LLMCallError, QueueAdmissionError) as exc:
        response = error_response(exc)
        logger.error(
            "Analysis failed code=%s retryable=%s request_id=%s",
            exc.code,
            exc.retryable,
            exc.request_id,
            exc_info=True,
        )
        return response
    except SafetyCheckError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "safety": {"hit_words": exc.hit_words},
            },
        )


@router.get("/analysis-jobs/{job_id}")
async def get_analysis_job(job_id: str):
    """Poll a queued analysis job without exposing provider internals."""
    status = get_job_queue().get_status(job_id)
    if status is None:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {"code": "JOB_NOT_FOUND", "message": "任务不存在或已过期。", "retryable": False},
                "message": "任务不存在或已过期。",
            },
        )
    return {"success": status["status"] == "SUCCESS", **status}
