"""
app/api/dependencies.py

Dependency injection for API routes.
"""

from functools import lru_cache

from core.config import get_settings
from services.analysis import AnalysisService


@lru_cache(maxsize=1)
def get_analysis_service() -> AnalysisService:
    """Cached analysis service singleton."""
    return AnalysisService(get_settings())
