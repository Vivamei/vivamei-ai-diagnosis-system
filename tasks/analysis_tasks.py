"""Background tasks that run the LLM-heavy analysis pipeline."""

from __future__ import annotations

import asyncio
import logging

from celery.exceptions import Ignore

from core.config import get_settings
from core.exceptions import AppException
from core.redis_client import get_redis
from services.analysis import AnalysisService
from services.queueing import RedisAdmissionGate

from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _gate() -> RedisAdmissionGate:
    settings = get_settings()
    return RedisAdmissionGate(
        get_redis(),
        user_requests_per_minute=settings.queue_user_requests_per_minute,
        user_max_active_jobs=settings.queue_user_max_active_jobs,
        ip_requests_per_minute=settings.queue_ip_requests_per_minute,
        ip_max_active_jobs=settings.queue_ip_max_active_jobs,
        global_max_queued_jobs=settings.queue_global_max_queued_jobs,
        job_ttl_seconds=settings.queue_job_ttl_seconds,
    )


@celery_app.task(bind=True, name="vivamei.analyze_image", max_retries=300)
def analyze_image_task(self, image_url: str, user_id: str, client_ip: str) -> dict:
    """Run one job after an execution lease becomes available."""
    settings = get_settings()
    gate = _gate()
    job_id = self.request.id
    gate.mark_started(job_id)

    if not gate.try_acquire_execution(
        job_id,
        max_inflight=settings.queue_global_max_inflight,
        lease_seconds=settings.queue_execution_lease_seconds,
    ):
        raise self.retry(countdown=2)

    try:
        return asyncio.run(
            AnalysisService(settings).analyze_stored_image_url_async(image_url, user_id=user_id)
        )
    except AppException as exc:
        self.update_state(
            # FAILURE is a Celery reserved state: a dict there is decoded as
            # serialized exception metadata and must contain exc_type.  Keep
            # safe client-facing details in our own terminal state instead.
            state="FAILED",
            meta={"code": exc.code, "message": exc.message, "retryable": exc.retryable},
        )
        raise Ignore() from exc
    except Exception as exc:
        logger.exception("Queued analysis failed job_id=%s", job_id)
        self.update_state(
            state="FAILED",
            meta={"code": "ANALYSIS_FAILED", "message": "分析任务未能完成，请稍后重试。", "retryable": True},
        )
        raise Ignore() from exc
    finally:
        gate.release_execution(job_id)
        gate.release_submission(user_id, client_ip, queued=False)
