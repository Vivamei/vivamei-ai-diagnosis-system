import asyncio
import json
import time
from datetime import datetime

from loguru import logger
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.analysis_task import AnalysisTask, TaskStatus
from app.models.photo import Photo
from app.models.report import Report, ReportModerationStatus
from app.services import analyze_queue as queue
from app.services.llm import LLMRequest, get_llm_provider
from app.services.llm.mock import MockLLMProvider
from app.services.moderation import scan_text
from app.services.oss import is_oss_configured, read_local_object, signed_download_url
from app.services.sensitive_words import contains_banned


async def run_analysis(*, task_id: str, redis, frame_delay: float | None = None) -> None:
    """后台分析任务。

    流程：
      1. 标记 task=streaming
      2. 调 LLM，逐事件推 SSE buffer + 累积 payload/delta/radar
      3. 全文做文本机审（本地词库 + 阿里云）
      4. 落 Report + 标记 task 终态
      5. 推 done/error 事件收尾
    """
    from app.services.sse_buffer import SseBuffer

    buf = SseBuffer(redis, task_id)
    _run_t0 = time.perf_counter()

    # 加载 task + photo
    async with SessionLocal() as s:
        task = (
            await s.execute(select(AnalysisTask).where(AnalysisTask.id == task_id))
        ).scalar_one()
        photo = (
            await s.execute(select(Photo).where(Photo.id == task.photo_id))
        ).scalar_one()
        _queue_gap = (datetime.utcnow() - task.created_at).total_seconds()
        logger.info(
            "[analyze] task={} 后台开始，排队等待 {:.1f}s（建任务→后台启动）",
            task_id,
            _queue_gap,
        )
        task.status = TaskStatus.streaming
        task.started_at = datetime.utcnow()
        await s.commit()

    provider = get_llm_provider()
    logger.info(
        "[analyze] task={} using provider={}", task_id, getattr(provider, "name", type(provider).__name__)
    )
    # 测试期注入加速
    if frame_delay is not None and isinstance(provider, MockLLMProvider):
        provider.frame_delay = frame_delay

    # 排队削峰：并发槽有限（analyze_max_concurrency），拿不到就在此等待，
    # 每 ~2s 推一个 queued 事件告知前端「前面还有几人」。拿到槽后再读图、调 LLM，
    # 保证排队期间不占用图片内存、也不打爆下游。槽在 finally 里释放。
    queue.register(task_id)
    acquire_task = asyncio.ensure_future(queue.acquire())
    slot_held = False
    try:
        while True:
            done_set, _ = await asyncio.wait({acquire_task}, timeout=2.0)
            if acquire_task in done_set:
                slot_held = True
                queue.unregister(task_id)
                break
            ahead = queue.position(task_id)
            await buf.push(
                "queued", json.dumps({"type": "queued", "ahead": ahead})
            )

        # 配了 OSS：给贵方签名 URL 自行拉图；没配 OSS：回读本地字节，走 file 上传。
        if is_oss_configured():
            image_url = signed_download_url(photo.oss_key)
            req = LLMRequest(task_id=task_id, image_url=image_url, user_id=task.user_id)
            logger.info(
                "[analyze] task={} 传图方式=OSS链接 oss_key={} url={}",
                task_id,
                photo.oss_key,
                image_url,
            )
        else:
            image_bytes = read_local_object(photo.oss_key)
            req = LLMRequest(
                task_id=task_id,
                image_bytes=image_bytes,
                image_mime=photo.mime or "image/jpeg",
                user_id=task.user_id,
            )
            logger.info(
                "[analyze] task={} 传图方式=file字节 oss_key={} bytes={}",
                task_id,
                photo.oss_key,
                len(image_bytes),
            )

        payloads: dict[str, dict] = {}
        radar: dict[str, int] | None = None
        delta_buf: dict[str, list[str]] = {
            p: [] for p in ("stype", "style", "subzone", "struct")
        }
        optimization: str = ""
        report_extra: dict = {}

        try:
            async for ev in provider.analyze_stream(req):
                await buf.push(ev.type, ev.model_dump_json(exclude_none=True))

                if ev.type == "delta" and ev.phase and ev.text:
                    delta_buf[ev.phase].append(ev.text)
                elif ev.type == "phase_done" and ev.phase and ev.payload:
                    payloads[ev.phase] = ev.payload
                elif ev.type == "radar" and ev.radar:
                    radar = ev.radar
                elif ev.type == "done" and ev.payload:
                    optimization = ev.payload.get("optimization", "") or ""
                    report_extra = ev.payload.get("extra") or {}
                elif ev.type == "error":
                    logger.warning(
                        "[analyze] task={} failed via LLM error: code={} message={}",
                        task_id,
                        (ev.error or {}).get("code"),
                        (ev.error or {}).get("message"),
                    )
                    async with SessionLocal() as s:
                        t = (
                            await s.execute(
                                select(AnalysisTask).where(AnalysisTask.id == task_id)
                            )
                        ).scalar_one()
                        t.status = TaskStatus.failed
                        t.error_code = (ev.error or {}).get("code")
                        t.error_message = (ev.error or {}).get("message")
                        t.finished_at = datetime.utcnow()
                        await s.commit()
                    return

            # 全文拼接 + 文本机审
            full_text = "\n".join(
                ["".join(delta_buf[p]) for p in ("style", "stype", "subzone", "struct")]
            )
            text_ok = (await scan_text(full_text)).passed and not contains_banned(full_text)

            async with SessionLocal() as s:
                rep = Report(
                    task_id=task_id,
                    schema_version="v1",
                    stype=payloads.get("stype", {}),
                    style=payloads.get("style", {}),
                    subzone=payloads.get("subzone", {}),
                    struct_=payloads.get("struct", {}),
                    radar_scores=radar or {"stype": 0, "style": 0, "subzone": 0, "struct": 0},
                    optimization=optimization,
                    extra=report_extra,
                    full_text=full_text,
                    moderation_status=(
                        ReportModerationStatus.passed
                        if text_ok
                        else ReportModerationStatus.rejected
                    ),
                )
                s.add(rep)
                t = (
                    await s.execute(
                        select(AnalysisTask).where(AnalysisTask.id == task_id)
                    )
                ).scalar_one()
                t.status = TaskStatus.done if text_ok else TaskStatus.moderated_out
                t.finished_at = datetime.utcnow()
                await s.commit()
                await s.refresh(rep)

            if not text_ok:
                await buf.push(
                    "error",
                    json.dumps(
                        {
                            "type": "error",
                            "error": {
                                "code": "REPORT_MODERATED_OUT",
                                "retryable": False,
                            },
                        }
                    ),
                )
            else:
                await buf.push(
                    "done",
                    json.dumps(
                        {
                            "type": "done",
                            "payload": {"taskId": task_id, "reportId": rep.id},
                        }
                    ),
                )
            logger.info(
                "[analyze] task={} 完成，后台总耗时 {:.1f}s",
                task_id,
                time.perf_counter() - _run_t0,
            )
        except Exception as e:
            logger.exception("analyze runner failed")
            async with SessionLocal() as s:
                t = (
                    await s.execute(
                        select(AnalysisTask).where(AnalysisTask.id == task_id)
                    )
                ).scalar_one()
                t.status = TaskStatus.failed
                t.error_code = "RUNNER_EXCEPTION"
                t.error_message = str(e)[:1000]
                t.finished_at = datetime.utcnow()
                await s.commit()
            await buf.push(
                "error",
                json.dumps(
                    {
                        "type": "error",
                        "error": {"code": "RUNNER_EXCEPTION", "retryable": True},
                    }
                ),
            )
    finally:
        queue.unregister(task_id)
        if slot_held:
            queue.release()
        else:
            # 还没拿到槽就退出了（异常/取消）：取消挂起的 acquire，避免占着信号量泄漏。
            # 若 cancel 前恰好拿到了槽，await 会正常返回，此时补一次 release。
            acquire_task.cancel()
            try:
                await acquire_task
            except (asyncio.CancelledError, Exception):
                pass
            else:
                queue.release()
