"""Submission-side service for durable analysis jobs."""

from __future__ import annotations

import uuid
from typing import Any

from services.queueing import RedisAdmissionGate


class AnalysisJobQueue:
    """Admit a job once, persist its ownership marker, then enqueue it."""

    def __init__(
            self,
            settings: Any,
            redis: Any,
            gate: RedisAdmissionGate,
            analysis_task: Any,
            image_service: Any | None = None,
    ):
        self.settings = settings
        self.redis = redis
        self.gate = gate
        self.analysis_task = analysis_task
        self.image_service = image_service

    @staticmethod
    def _job_key(job_id: str) -> str:
        return f"v3:job:{job_id}"

    def submit_url(self, image_url: str, user_id: str | None, client_ip: str) -> dict:
        """Create a queued task after the Redis admission gate accepts it."""
        job_id = uuid.uuid4().hex

        normalized_user_id = self.gate.admit(user_id, client_ip, job_id)

        try:
            self.redis.setex(
                self._job_key(job_id),
                self.settings.queue_job_ttl_seconds,
                "1",
            )
            self.analysis_task.apply_async(
                args=(image_url, normalized_user_id, client_ip),
                task_id=job_id,
            )
        except Exception:
            self.gate.release_submission(normalized_user_id, client_ip, queued=True)
            raise
        return {"job_id": job_id, "status": "QUEUED"}

    def submit_file(self, file: Any, user_id: str | None, client_ip: str) -> dict:
        """Store a file first, then enqueue it with the same admission safeguards."""
        if self.image_service is None:
            from services.image import ImageService
            self.image_service = ImageService(self.settings)

        job_id = uuid.uuid4().hex

        normalized_user_id = self.gate.admit(user_id, client_ip, job_id)

        try:
            image_path = self.image_service.save_upload(file)
            image_url = self.image_service.build_public_url(image_path)

            self.redis.setex(
                self._job_key(job_id),
                self.settings.queue_job_ttl_seconds,
                "1",
            )
            self.analysis_task.apply_async(
                args=(image_url, normalized_user_id, client_ip),
                task_id=job_id,
            )
        except Exception:
            self.gate.release_submission(normalized_user_id, client_ip, queued=True)
            raise
        return {"job_id": job_id, "status": "QUEUED"}

    def get_status(self, job_id: str) -> dict | None:
        """Return a stable polling representation without exposing tracebacks."""
        if not self.redis.exists(self._job_key(job_id)):
            return None

        try:
            result = self.analysis_task.AsyncResult(job_id)
            state = result.state
        except ValueError as exc:
            # Jobs created by the former implementation stored a plain dict
            # in Celery's reserved FAILURE state.  Celery cannot deserialize
            # it as an exception; keep polling safe until the result expires.
            if "Exception information must include the exception type" not in str(exc):
                raise
            return {
                "job_id": job_id,
                "status": "FAILURE",
                "error": {
                    "code": "ANALYSIS_FAILED",
                    "message": "历史任务状态无效，请重新提交分析。",
                    "retryable": True,
                },
            }

        if state == "SUCCESS":
            return {"job_id": job_id, "status": "SUCCESS", "result": result.result}
        if state in {"FAILED", "FAILURE"}:
            info = result.info if isinstance(result.info, dict) else {}
            return {
                "job_id": job_id,
                "status": "FAILURE",
                "error": {
                    "code": info.get("code", "ANALYSIS_FAILED"),
                    "message": info.get("message", "分析任务未能完成，请稍后重试。"),
                    "retryable": bool(info.get("retryable", True)),
                },
            }
        response = {"job_id": job_id, "status": "RUNNING" if state == "STARTED" else "QUEUED"}
        if state == "RETRY":
            response["retry_after_seconds"] = 2
        return response
