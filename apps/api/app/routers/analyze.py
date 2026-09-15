import asyncio
import json

import ulid
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse
from jose import JWTError
from loguru import logger
from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.deps.auth import CurrentUser, get_current_user
from app.deps.db import get_db
from app.deps.redis import get_redis
from app.models.analysis_task import AnalysisTask, TaskStatus
from app.models.photo import ModerationStatus, Photo
from app.models.user import User
from app.schemas.analyze import AnalyzeCreateRequest, AnalyzeCreateResponse
from app.services.analyze_runner import run_analysis
from app.services.ratelimit import RateLimiter
from app.services.sse_buffer import SseBuffer

router = APIRouter(prefix="/api/analyze", tags=["analyze"])


@router.get("/quota")
async def analyze_quota(
    user: CurrentUser = Depends(get_current_user),
    r=Depends(get_redis),
):
    """前置查询当前用户今日剩余生成次数，用于「开始测一测」点击时拦截，只读不消耗配额。"""
    limit = settings.rl_analyze_per_day
    used = await RateLimiter(
        r, f"rl:user:{user.id}:analyze:d", limit, 86400
    ).peek()
    return {"blocked": used >= limit, "remaining": max(0, limit - used), "limit": limit}


@router.post("", response_model=AnalyzeCreateResponse, status_code=202)
async def create_analyze(
    req: AnalyzeCreateRequest,
    bg: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db),
    r=Depends(get_redis),
):
    logger.info(
        "[analyze] create user={} body={}",
        user.id,
        req.model_dump_json(),
    )
    # 限流：每用户每小时 N / 每天 N
    h_rl = RateLimiter(
        r, f"rl:user:{user.id}:analyze:h", settings.rl_analyze_per_hour, 3600
    )
    d_rl = RateLimiter(
        r, f"rl:user:{user.id}:analyze:d", settings.rl_analyze_per_day, 86400
    )
    hour_ok = await h_rl.allow()
    day_ok = await d_rl.allow()
    if not (hour_ok and day_ok):
        window = "hour" if not hour_ok else "day"
        limit = (
            settings.rl_analyze_per_hour if not hour_ok else settings.rl_analyze_per_day
        )
        logger.warning(
            "[analyze] rate limited user={} window={} limit={}",
            user.id,
            window,
            limit,
        )
        raise AppError(
            "ANALYZE_RATE_LIMITED",
            f"分析次数过多（{window} 上限 {limit}）",
            status_code=429,
        )

    photo = (
        await db.execute(
            select(Photo).where(Photo.id == req.photoId, Photo.user_id == user.id)
        )
    ).scalar_one_or_none()
    if not photo:
        raise AppError("PHOTO_NOT_FOUND", "photo not found", status_code=404)
    if photo.moderation_status == ModerationStatus.rejected:
        raise AppError(
            "PHOTO_MODERATION_REJECTED",
            "图片未通过内容审核",
            status_code=422,
        )
    if photo.moderation_status == ModerationStatus.pending:
        raise AppError(
            "PHOTO_MODERATION_PENDING", "图片审核中，请稍后", status_code=425
        )

    task_id = str(ulid.new())
    task = AnalysisTask(
        id=task_id,
        user_id=user.id,
        photo_id=photo.id,
        status=TaskStatus.queued,
        llm_provider=settings.llm_provider,
    )
    db.add(task)
    await db.commit()
    bg.add_task(
        run_analysis,
        task_id=task_id,
        redis=r,
        frame_delay=settings.mock_frame_delay,
    )
    return AnalyzeCreateResponse(taskId=task_id, status="queued")


@router.get("/{task_id}/stream")
async def analyze_stream(
    task_id: str,
    request: Request,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
    r=Depends(get_redis),
):
    # SSE 走 EventSource 无法带 Header，允许 ?token=<accessToken> 回退
    raw = None
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization.split(" ", 1)[1]
    elif token:
        raw = token
    if not raw:
        raise AppError("AUTH_REQUIRED", "missing token", status_code=401)
    try:
        claims = decode_token(raw)
    except JWTError:
        raise AppError("AUTH_INVALID_TOKEN", "invalid token", status_code=401)
    if claims.get("type") != "access":
        raise AppError("AUTH_INVALID_TOKEN", "wrong token type", status_code=401)
    if await r.exists(f"jwt:blacklist:{raw}"):
        raise AppError("AUTH_INVALID_TOKEN", "token revoked", status_code=401)
    uid = int(claims["sub"])
    # 只在鉴权/查任务时短暂占用 DB 连接，查完即释放。StreamingResponse 会把请求作用域
    # 的依赖（含 Depends(get_db)）一直挂到流结束（2-3 分钟），而 gen() 只用 Redis，不用 DB。
    # 若走 Depends(get_db)，每条打开的 SSE 流都会钉住一个 DB 连接直到流关闭，并发上限被
    # DB 连接池/MySQL max_connections 卡死。这里改用独立短会话，让并发流数与 DB 池解耦。
    async with SessionLocal() as db:
        u = (
            await db.execute(
                select(User).where(User.id == uid, User.deleted_at.is_(None))
            )
        ).scalar_one_or_none()
        if not u:
            raise AppError("AUTH_INVALID_TOKEN", "user not found", status_code=401)
        user = CurrentUser(id=u.id, nickname=u.nickname)

        task = (
            await db.execute(
                select(AnalysisTask).where(
                    AnalysisTask.id == task_id, AnalysisTask.user_id == user.id
                )
            )
        ).scalar_one_or_none()
        if not task:
            raise AppError("TASK_NOT_FOUND", "task not found", status_code=404)

    buf = SseBuffer(r, task_id)

    async def gen():
        # 持续 tail：从 last_event_id（若有）向后读，写完一批就 sleep 一会再看有没有新事件。
        # 命中 done/error 事件即结束；期间兼顾心跳与断连检测。
        last_seen: str | None = last_event_id
        end_types = {"done", "error"}
        seen_end = False
        idle_ticks = 0

        while not seen_end:
            if await request.is_disconnected():
                break

            emitted = 0
            async for mid, event, data in buf.replay(last_id=last_seen):
                yield f"id: {mid}\nevent: {event}\ndata: {data}\n\n"
                last_seen = mid
                emitted += 1
                if event in end_types:
                    seen_end = True
                    break

            if seen_end:
                break

            if emitted == 0:
                idle_ticks += 1
                # 每 ~30s 发一次心跳，防 Nginx 切流
                if idle_ticks >= 100:  # 100 * 0.3s = 30s
                    yield ": ping\n\n"
                    idle_ticks = 0
                await asyncio.sleep(0.3)
            else:
                idle_ticks = 0

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _ws_auth(task_id: str, raw: str | None, r) -> None:
    """WS 鉴权 + 任务归属校验，失败抛 AppError（由调用方转成 close code）。"""
    if not raw:
        raise AppError("AUTH_REQUIRED", "missing token", status_code=401)
    try:
        claims = decode_token(raw)
    except JWTError:
        raise AppError("AUTH_INVALID_TOKEN", "invalid token", status_code=401)
    if claims.get("type") != "access":
        raise AppError("AUTH_INVALID_TOKEN", "wrong token type", status_code=401)
    if await r.exists(f"jwt:blacklist:{raw}"):
        raise AppError("AUTH_INVALID_TOKEN", "token revoked", status_code=401)
    uid = int(claims["sub"])
    # 同 SSE：只在鉴权时短暂借一条 DB 连接，tail 阶段只用 Redis，不钉住连接池。
    async with SessionLocal() as db:
        u = (
            await db.execute(
                select(User).where(User.id == uid, User.deleted_at.is_(None))
            )
        ).scalar_one_or_none()
        if not u:
            raise AppError("AUTH_INVALID_TOKEN", "user not found", status_code=401)
        task = (
            await db.execute(
                select(AnalysisTask).where(
                    AnalysisTask.id == task_id, AnalysisTask.user_id == u.id
                )
            )
        ).scalar_one_or_none()
        if not task:
            raise AppError("TASK_NOT_FOUND", "task not found", status_code=404)


@router.websocket("/{task_id}/ws")
async def analyze_ws(
    ws: WebSocket,
    task_id: str,
    token: str | None = Query(default=None),
    last_event_id: str | None = Query(default=None, alias="lastEventId"),
    r=Depends(get_redis),
):
    """SSE 的小程序版：小程序没有 EventSource，改用 WebSocket 推同一份事件流。

    读的是同一个 SseBuffer（Redis Stream），事件语义、断线重连的 lastEventId 续传
    都与 /stream 一致，analyze_runner 无需改动。H5 继续走 SSE。
    """
    await ws.accept()
    try:
        await _ws_auth(task_id, token, r)
    except AppError as e:
        await ws.send_text(
            json.dumps({"event": "error", "data": json.dumps({"code": e.code, "message": e.message})})
        )
        # 4401/4404 属自定义区间（4000-4999），小程序端据此区分「重新登录」与「任务不存在」
        await ws.close(code=4401 if e.status_code == 401 else 4404)
        return

    buf = SseBuffer(r, task_id)
    last_seen: str | None = last_event_id
    end_types = {"done", "error"}

    try:
        while True:
            emitted = 0
            seen_end = False
            async for mid, event, data in buf.replay(last_id=last_seen):
                # data 已是 JSON 字符串，原样透传，客户端解析方式与 SSE 完全一致
                await ws.send_text(
                    json.dumps({"id": mid, "event": event, "data": data})
                )
                last_seen = mid
                emitted += 1
                if event in end_types:
                    seen_end = True
                    break
            if seen_end:
                break
            if emitted == 0:
                await asyncio.sleep(0.3)
    except WebSocketDisconnect:
        return

    await ws.close()
