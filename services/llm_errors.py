"""Safe provider error classification and bounded retry helpers."""

from __future__ import annotations

import asyncio
import random
import re
import time
from typing import Any, Awaitable, Callable, TypeVar

from core.exceptions import LLMCallError


T = TypeVar("T")


def _status_code(exc: Exception) -> int | None:
    for attr in ("status_code", "status"):
        value = getattr(exc, attr, None)
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            pass
    match = re.search(r"(?:error\s+code|status(?:_code)?)\s*[:=]?\s*(\d{3})", str(exc), re.I)
    return int(match.group(1)) if match else None


def classify_llm_exception(exc: Exception) -> LLMCallError:
    """Map raw SDK/provider failures to a stable, non-secret client error."""
    if isinstance(exc, LLMCallError):
        return exc

    raw = str(exc)
    text = raw.lower()
    status = _status_code(exc)

    if any(token in text for token in ("arrearage", "overdue-payment", "insufficient_quota", "billing")):
        return LLMCallError(
            "大模型账户状态异常，请联系管理员检查余额或服务状态。",
            code="LLM_BILLING_ERROR",
            status_code=503,
            retryable=False,
        )
    if any(token in text for token in ("failed to download multimodal content", "failed to download image", "image url is invalid")):
        return LLMCallError(
            "大模型无法读取上传图片，请重新上传后再试。",
            code="LLM_IMAGE_UNAVAILABLE",
            status_code=422,
            retryable=False,
        )
    if status in (401, 403) or any(
        token in text
        for token in ("invalid api key", "incorrect api key", "authentication", "permission denied", "unauthorized", "forbidden")
    ):
        return LLMCallError(
            "大模型鉴权失败，请联系管理员检查 API Key 与服务权限。",
            code="LLM_AUTH_ERROR",
            status_code=503,
            retryable=False,
        )
    if any(token in text for token in ("model_not_found", "model not found", "model does not exist", "invalid model")):
        return LLMCallError(
            "大模型配置不可用，请联系管理员检查模型名称与权限。",
            code="LLM_MODEL_ERROR",
            status_code=503,
            retryable=False,
        )
    if status == 429 or any(token in text for token in ("rate limit", "too many requests", "throttl")):
        return LLMCallError(
            "大模型服务当前请求较多，请稍后重试。",
            code="LLM_RATE_LIMITED",
            status_code=503,
            retryable=True,
        )
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or any(
        token in text for token in ("timed out", "timeout", "read timeout", "connect timeout")
    ):
        return LLMCallError(
            "大模型响应超时，请稍后重试。",
            code="LLM_TIMEOUT",
            status_code=504,
            retryable=True,
        )
    if status in (502, 503, 504) or any(
        token in text
        for token in ("service unavailable", "bad gateway", "gateway timeout", "connection reset", "connection error")
    ):
        return LLMCallError(
            "大模型服务暂时不可用，请稍后重试。",
            code="LLM_UPSTREAM_UNAVAILABLE",
            status_code=503,
            retryable=True,
        )
    if status == 400 or any(token in text for token in ("invalid_parameter", "invalid parameter", "bad request")):
        return LLMCallError(
            "大模型拒绝了本次请求，请重新上传符合要求的图片。",
            code="LLM_BAD_REQUEST",
            status_code=422,
            retryable=False,
        )
    return LLMCallError(
        "大模型调用失败，请稍后再试或联系管理员。",
        code="LLM_CALL_ERROR",
        status_code=502,
        retryable=False,
    )


def _delay(attempt_index: int) -> float:
    return 0.25 * (2**attempt_index) + random.uniform(0.0, 0.05)


def retry_sync(
    operation: Callable[[], T],
    *,
    max_attempts: int = 2,
    sleep: Callable[[float], Any] = time.sleep,
) -> T:
    """Run a synchronous provider operation with at most one retry by default."""
    for attempt in range(max_attempts):
        try:
            return operation()
        except Exception as exc:
            error = classify_llm_exception(exc)
            if not error.retryable or attempt + 1 >= max_attempts:
                raise error from exc
            sleep(_delay(attempt))
    raise AssertionError("unreachable")


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 2,
    sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
) -> T:
    """Run an asynchronous provider operation with at most one retry by default."""
    for attempt in range(max_attempts):
        try:
            return await operation()
        except Exception as exc:
            error = classify_llm_exception(exc)
            if not error.retryable or attempt + 1 >= max_attempts:
                raise error from exc
            await sleep(_delay(attempt))
    raise AssertionError("unreachable")
