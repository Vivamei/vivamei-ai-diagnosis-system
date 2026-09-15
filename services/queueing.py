"""Redis-backed queue admission, execution leases, and safe release helpers."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any

from core.exceptions import AppException


ADMISSION_LUA = """
local user_rate = tonumber(redis.call('GET', KEYS[1]) or '0')
if user_rate >= tonumber(ARGV[1]) then
  return {0, 'USER_RATE_LIMIT', redis.call('TTL', KEYS[1])}
end
local user_active = tonumber(redis.call('GET', KEYS[2]) or '0')
if user_active >= tonumber(ARGV[3]) then
  return {0, 'USER_ACTIVE_LIMIT', redis.call('TTL', KEYS[2])}
end
local ip_rate = tonumber(redis.call('GET', KEYS[3]) or '0')
if ip_rate >= tonumber(ARGV[4]) then
  return {0, 'IP_RATE_LIMIT', redis.call('TTL', KEYS[3])}
end
local ip_active = tonumber(redis.call('GET', KEYS[4]) or '0')
if ip_active >= tonumber(ARGV[6]) then
  return {0, 'IP_ACTIVE_LIMIT', redis.call('TTL', KEYS[4])}
end
local waiting = tonumber(redis.call('GET', KEYS[5]) or '0')
if waiting >= tonumber(ARGV[7]) then
  return {0, 'GLOBAL_QUEUE_FULL', redis.call('TTL', KEYS[5])}
end
local next_user_rate = redis.call('INCR', KEYS[1])
if next_user_rate == 1 then redis.call('EXPIRE', KEYS[1], ARGV[2]) end
local next_ip_rate = redis.call('INCR', KEYS[3])
if next_ip_rate == 1 then redis.call('EXPIRE', KEYS[3], ARGV[5]) end
redis.call('INCR', KEYS[2])
redis.call('EXPIRE', KEYS[2], ARGV[8])
redis.call('INCR', KEYS[4])
redis.call('EXPIRE', KEYS[4], ARGV[8])
redis.call('INCR', KEYS[5])
if waiting == 0 then redis.call('EXPIRE', KEYS[5], ARGV[8]) end
return {1, 'OK', 0}
""".strip()

RELEASE_SUBMISSION_LUA = """
local user_active = tonumber(redis.call('GET', KEYS[1]) or '0')
if user_active > 0 then redis.call('DECR', KEYS[1]) end
local ip_active = tonumber(redis.call('GET', KEYS[2]) or '0')
if ip_active > 0 then redis.call('DECR', KEYS[2]) end
if tonumber(ARGV[1]) == 1 then
  local waiting = tonumber(redis.call('GET', KEYS[3]) or '0')
  if waiting > 0 then redis.call('DECR', KEYS[3]) end
end
return 1
""".strip()

EXECUTION_LEASE_LUA = """
local now = tonumber(ARGV[1])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then return 0 end
redis.call('ZADD', KEYS[1], tonumber(ARGV[3]), ARGV[4])
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[5]))
return 1
""".strip()


class QueueAdmissionError(AppException):
    """Intentional queue protection response; never represented as a false 202."""

    def __init__(self, code: str, message: str, status_code: int, retry_after: int):
        super().__init__(
            message,
            status_code=status_code,
            code=code,
            retryable=True,
            details={"retry_after_seconds": max(1, int(retry_after or 1))},
        )


class UserIdentityError(QueueAdmissionError):
    """Invalid login identity supplied to a queue-mode request."""

    def __init__(self, code: str, message: str):
        AppException.__init__(
            self,
            message,
            status_code=400,
            code=code,
            retryable=False,
        )


@dataclass(frozen=True)
class AdmissionKeys:
    user_rate: str
    user_active: str
    ip_rate: str
    ip_active: str
    waiting: str


class RedisAdmissionGate:
    """Use Redis Lua so all API replicas apply identical queue limits atomically."""

    def __init__(
        self,
        redis: Any,
        user_requests_per_minute: int,
        user_max_active_jobs: int,
        ip_requests_per_minute: int,
        ip_max_active_jobs: int,
        global_max_queued_jobs: int,
        job_ttl_seconds: int,
    ):
        self.redis = redis
        self.user_requests_per_minute = user_requests_per_minute
        self.user_max_active_jobs = user_max_active_jobs
        self.ip_requests_per_minute = ip_requests_per_minute
        self.ip_max_active_jobs = ip_max_active_jobs
        self.global_max_queued_jobs = global_max_queued_jobs
        self.job_ttl_seconds = job_ttl_seconds

    @staticmethod
    def hash_ip(ip: str) -> str:
        return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def hash_user(user_id: str) -> str:
        return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def normalize_user_id(user_id: str | None) -> str:
        if user_id is None or not isinstance(user_id, str) or not user_id.strip():
            raise UserIdentityError("USER_ID_REQUIRED", "排队分析需要有效的登录用户 ID。")
        normalized = user_id.strip()
        if len(normalized) > 128:
            raise UserIdentityError("USER_ID_INVALID", "用户 ID 长度不能超过 128 个字符。")
        return normalized

    @classmethod
    def keys(cls, user_id: str, ip: str) -> AdmissionKeys:
        user_hash = cls.hash_user(user_id)
        ip_hash = cls.hash_ip(ip)
        return AdmissionKeys(
            f"v3:user-rate:{user_hash}",
            f"v3:user-active:{user_hash}",
            f"v3:ip-rate:{ip_hash}",
            f"v3:ip-active:{ip_hash}",
            "v3:queue:waiting",
        )

    def admit(self, user_id: str | None, client_ip: str, job_id: str) -> str:
        del job_id
        normalized_user_id = self.normalize_user_id(user_id)
        keys = self.keys(normalized_user_id, client_ip)
        allowed, reason, retry_after = self.redis.eval(
            ADMISSION_LUA,
            5,
            keys.user_rate,
            keys.user_active,
            keys.ip_rate,
            keys.ip_active,
            keys.waiting,
            self.user_requests_per_minute,
            60,
            self.user_max_active_jobs,
            self.ip_requests_per_minute,
            60,
            self.ip_max_active_jobs,
            self.global_max_queued_jobs,
            self.job_ttl_seconds,
        )
        if int(allowed):
            return normalized_user_id
        reason = reason.decode() if isinstance(reason, bytes) else str(reason)
        error_map = {
            "USER_RATE_LIMIT": ("USER_RATE_LIMITED", "当前用户提交过于频繁，请稍后再试。", 429),
            "USER_ACTIVE_LIMIT": ("USER_QUEUE_LIMITED", "当前用户排队任务较多，请等待现有任务完成。", 429),
            "IP_RATE_LIMIT": ("IP_RATE_LIMITED", "当前网络提交过于频繁，请稍后再试。", 429),
            "IP_ACTIVE_LIMIT": ("IP_QUEUE_LIMITED", "当前网络排队任务较多，请等待现有任务完成。", 429),
            "GLOBAL_QUEUE_FULL": ("QUEUE_FULL", "当前分析队列较满，请稍后再提交。", 503),
        }
        code, message, status = error_map.get(reason, ("QUEUE_UNAVAILABLE", "任务队列暂时不可用，请稍后再试。", 503))
        raise QueueAdmissionError(code, message, status, int(retry_after or 1))

    def mark_started(self, job_id: str) -> bool:
        """Decrement waiting once, even when Celery retries the same task."""
        if not self.redis.set(f"v3:job-started:{job_id}", "1", nx=True, ex=self.job_ttl_seconds):
            return False
        self.redis.decr("v3:queue:waiting")
        return True

    def try_acquire_execution(self, job_id: str, *, max_inflight: int, lease_seconds: int) -> bool:
        now = int(time.time())
        result = self.redis.eval(
            EXECUTION_LEASE_LUA, 1, "v3:analysis:inflight", now, max_inflight,
            now + lease_seconds, job_id, lease_seconds,
        )
        return bool(int(result))

    def release_execution(self, job_id: str) -> None:
        self.redis.zrem("v3:analysis:inflight", job_id)

    def release_submission(self, user_id: str, client_ip: str, *, queued: bool) -> None:
        """Release a completed/failed admission; TTL remains the crash fallback."""
        keys = self.keys(user_id, client_ip)
        self.redis.eval(
            RELEASE_SUBMISSION_LUA,
            3,
            keys.user_active,
            keys.ip_active,
            keys.waiting,
            1 if queued else 0,
        )

QueueGate = RedisAdmissionGate
