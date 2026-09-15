"""
app/api/dependencies.py

Dependency injection for API routes.
"""

from functools import lru_cache

from core.config import get_settings
from core.redis_client import get_redis
from services.analysis import AnalysisService
from services.job_queue import AnalysisJobQueue
from services.queueing import RedisAdmissionGate
from tasks.analysis_tasks import analyze_image_task


@lru_cache(maxsize=1)
def get_analysis_service() -> AnalysisService:
    """Cached analysis service singleton."""
    return AnalysisService(get_settings())


@lru_cache(maxsize=1)
def get_job_queue() -> AnalysisJobQueue:
    """Cached admission gate and Celery task facade for public queue endpoints."""
    settings = get_settings()
    return AnalysisJobQueue(
        settings=settings,
        redis=get_redis(),
        gate=RedisAdmissionGate(
            get_redis(),
            user_requests_per_minute=settings.queue_user_requests_per_minute,
            user_max_active_jobs=settings.queue_user_max_active_jobs,
            ip_requests_per_minute=settings.queue_ip_requests_per_minute,
            ip_max_active_jobs=settings.queue_ip_max_active_jobs,
            global_max_queued_jobs=settings.queue_global_max_queued_jobs,
            job_ttl_seconds=settings.queue_job_ttl_seconds,
        ),
        analysis_task=analyze_image_task,
    )
