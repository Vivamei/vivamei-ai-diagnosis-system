"""
core/exceptions.py

Custom application exceptions with HTTP status codes.
"""


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        *,
        code: str = "INTERNAL_ERROR",
        retryable: bool = False,
        details: dict | None = None,
        request_id: str | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        self.retryable = retryable
        self.details = details or {}
        self.request_id = request_id
        super().__init__(self.message)


class ImageQualityError(AppException):
    """Image does not meet quality requirements."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message,
            status_code=400,
            code="IMAGE_QUALITY_ERROR",
            details=details,
        )


class SafetyCheckError(AppException):
    """Report failed safety/compliance check."""

    def __init__(self, message: str, hit_words: list[str] | None = None):
        super().__init__(message, status_code=200, code="SAFETY_CHECK_ERROR")
        self.hit_words = hit_words or []


class LLMCallError(AppException):
    """LLM API call failed."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "LLM_CALL_ERROR",
        status_code: int = 502,
        retryable: bool = False,
        details: dict | None = None,
        request_id: str | None = None,
    ):
        super().__init__(
            message,
            status_code=status_code,
            code=code,
            retryable=retryable,
            details=details,
            request_id=request_id,
        )


class ConfigurationError(AppException):
    """Missing or invalid configuration."""

    def __init__(self, message: str):
        super().__init__(message, status_code=500, code="CONFIG_ERROR")
