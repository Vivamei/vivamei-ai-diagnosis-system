import asyncio
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.analysis_task import AnalysisTask, TaskStatus
from app.services.analyze_runner import run_analysis
from app.services.sse_buffer import SseBuffer


async def recover_inflight_tasks(redis) -> None:
    """进程启动时重放「卡在 queued/streaming」的分析任务。

    背景：分析走进程内 BackgroundTasks（协程 + 内存信号量队列），worker 重启/崩溃会静默丢掉
    在途任务，DB 里留下永远卡在 queued/streaming 的行、前端 SSE 一直转圈。此函数在 lifespan
    启动时扫这些行，重新 dispatch run_analysis 让它们跑完（run_analysis 会重置状态、重签图片
    URL、重调下游，产出全新 Report——queued/streaming 期间尚未写 Report，故无重复入库风险）。

    多 worker（UVICORN_WORKERS>1）下每个 worker 都会跑一遍 lifespan，用 Redis SET NX 抢占
    claim 去重，保证每个 task 只被一个 worker 重放。超过 analyze_recover_max_age_seconds 的
    任务用户早已放弃，直接标记 failed 收尾，不再重放。
    """
    cutoff = datetime.utcnow() - timedelta(
        seconds=settings.analyze_recover_max_age_seconds
    )
    async with SessionLocal() as s:
        rows = (
            (
                await s.execute(
                    select(AnalysisTask).where(
                        AnalysisTask.status.in_(
                            [TaskStatus.queued, TaskStatus.streaming]
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
    if not rows:
        return

    replay = [t for t in rows if t.created_at >= cutoff]
    stale = [t for t in rows if t.created_at < cutoff]

    stale_done = 0
    for t in stale:
        async with SessionLocal() as s:
            row = (
                await s.execute(select(AnalysisTask).where(AnalysisTask.id == t.id))
            ).scalar_one()
            # 二次确认状态，避免另一 worker 已处理
            if row.status in (TaskStatus.queued, TaskStatus.streaming):
                row.status = TaskStatus.failed
                row.error_code = "RECOVERY_STALE"
                row.error_message = "任务在服务重启前未完成且已超时"
                row.finished_at = datetime.utcnow()
                await s.commit()
                stale_done += 1
    if stale_done:
        logger.info("[recovery] 标记 {} 个超时在途任务为 failed", stale_done)

    dispatched = 0
    for t in replay:
        # 多 worker 去重：抢到 claim 的 worker 才重放，其余跳过
        claimed = await redis.set(
            f"recover:claim:{t.id}",
            "1",
            nx=True,
            ex=settings.analyze_recover_max_age_seconds,
        )
        if not claimed:
            continue
        # 清掉重启前的半截 SSE buffer，让重放从干净状态开始（新 stream id 基于当前时间，
        # 晚于旧 id，前端持旧 Last-Event-ID 重连仍能收到新事件）
        await SseBuffer(redis, t.id).delete()
        asyncio.create_task(
            run_analysis(
                task_id=t.id,
                redis=redis,
                frame_delay=settings.mock_frame_delay,
            )
        )
        dispatched += 1

    if dispatched:
        logger.info("[recovery] 重放 {} 个在途分析任务", dispatched)
