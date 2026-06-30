"""
core/exceptions.py

Custom application exceptions with HTTP status codes.
"""


class AppException(Exception):
    """Base application exception."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ImageQualityError(AppException):
    """Image does not meet quality requirements."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, status_code=400)
        self.details = details or {}


class SafetyCheckError(AppException):
    """Report failed safety/compliance check."""

    def __init__(self, message: str, hit_words: list[str] | None = None):
        super().__init__(message, status_code=200)
        self.hit_words = hit_words or []


class LLMCallError(AppException):
    """LLM API call failed."""

    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class ConfigurationError(AppException):
    """Missing or invalid configuration."""

    def __init__(self, message: str):
        super().__init__(message, status_code=500)
