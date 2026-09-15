import hashlib
import hmac
import time

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import AppError
from app.deps.auth import CurrentUser, get_current_user
from app.deps.db import get_db
from app.deps.redis import get_redis
from app.models.analysis_task import AnalysisTask
from app.models.report import Report
from app.schemas.report import ReportResponse

router = APIRouter(prefix="/api/reports", tags=["reports"])

# 手机端 PDF 下载走顶层导航（不带 Authorization 头），用查询串短时签名 token 鉴权
_PDF_TOKEN_TTL = 900  # 15 分钟
# PDF 是一次性中转件：手机端上传后 15 分钟内跳转下载，用完即弃。存 Redis 靠 TTL
# 自动过期，不落库、不需清理 cron，避免大 blob 撑表和 MySQL max_allowed_packet 风险。
_PDF_REDIS_TTL = _PDF_TOKEN_TTL  # Redis 存活时长与下载 token 有效期一致
_PDF_MAX_BYTES = 8 * 1024 * 1024  # PDF 实际 1-3MB，留足余量即可


def _pdf_redis_key(task_id: str) -> str:
    return f"report_pdf:{task_id}"


def _sign_pdf_token(task_id: str) -> str:
    exp = int(time.time()) + _PDF_TOKEN_TTL
    sig = hmac.new(
        settings.jwt_secret.encode(), f"{task_id}.{exp}".encode(), hashlib.sha256
    ).hexdigest()
    return f"{exp}.{sig}"


def _verify_pdf_token(task_id: str, token: str) -> bool:
    try:
        exp_str, sig = token.split(".", 1)
        exp = int(exp_str)
    except (ValueError, AttributeError):
        return False
    if exp < int(time.time()):
        return False
    expected = hmac.new(
        settings.jwt_secret.encode(), f"{task_id}.{exp}".encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(sig, expected)


@router.get("/{task_id}", response_model=ReportResponse)
async def get_report(
    task_id: str,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
):
    t = (
        await db.execute(
            select(AnalysisTask).where(
                AnalysisTask.id == task_id, AnalysisTask.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if not t:
        raise AppError("TASK_NOT_FOUND", "task not found", status_code=404)

    rep = (
        await db.execute(select(Report).where(Report.task_id == task_id))
    ).scalar_one_or_none()
    if not rep:
        raise AppError("REPORT_NOT_READY", "report not ready", status_code=425)

    ex = rep.extra or {}
    return ReportResponse(
        taskId=rep.task_id,
        schemaVersion=rep.schema_version,
        stype=rep.stype,
        style=rep.style,
        subzone=rep.subzone,
        struct=rep.struct_,  # 数据库列名 struct_，对外暴露为 struct
        radarScores=rep.radar_scores,
        radar_semantics=ex.get("radar_semantics"),
        radar_max=ex.get("radar_max"),
        state_values=ex.get("state_values"),
        optimization=rep.optimization,
        aesthetic_optimization=ex.get("aesthetic_optimization"),
        project_directions=ex.get("project_directions"),
        mapped_project_directions=ex.get("mapped_project_directions"),
        lead_cta=ex.get("lead_cta"),
        disclaimer=ex.get("disclaimer"),
        image_quality=ex.get("image_quality"),
        createdAt=rep.created_at,
    )


@router.post("/{task_id}/pdf")
async def upload_report_pdf(
    task_id: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
    redis=Depends(get_redis),
):
    """前端渲染好的 PDF 字节暂存到 Redis（多 Pod 共享），返回带签名 token 的下载链接。

    微信 webview 打不开 blob: URL，故手机端出图后传这里，再跳转下面的 GET 下载。
    PDF 是一次性中转件，靠 Redis TTL 15 分钟后自动过期，不落库。
    """
    t = (
        await db.execute(
            select(AnalysisTask).where(
                AnalysisTask.id == task_id, AnalysisTask.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if not t:
        raise AppError("TASK_NOT_FOUND", "task not found", status_code=404)

    data = await request.body()
    if not data:
        raise AppError("EMPTY_BODY", "empty pdf body", status_code=400)
    if len(data) > _PDF_MAX_BYTES:
        raise AppError(
            "PDF_TOO_LARGE",
            f"PDF 超过上限 {_PDF_MAX_BYTES} bytes",
            status_code=413,
        )

    await redis.set(_pdf_redis_key(task_id), data, ex=_PDF_REDIS_TTL)

    # 相对路径：dev 走 vite 代理、prod 同源，前端用 location.origin 前缀即可
    return {"downloadUrl": f"/api/reports/{task_id}/pdf?token={_sign_pdf_token(task_id)}"}


@router.get("/{task_id}/pdf")
async def download_report_pdf(
    task_id: str,
    token: str = Query(...),
    redis=Depends(get_redis),
):
    """顶层导航下载 PDF：用查询串 token 鉴权，返回带 attachment 头的字节流。"""
    if not _verify_pdf_token(task_id, token):
        raise AppError("INVALID_TOKEN", "invalid or expired token", status_code=403)

    data = await redis.get(_pdf_redis_key(task_id))
    if not data:
        # 找不到多半是超过 15 分钟 TTL 过期了，提示重新导出
        raise AppError("PDF_NOT_FOUND", "pdf not found or expired", status_code=404)

    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="4s-report.pdf"'},
    )
