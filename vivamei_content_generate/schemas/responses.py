"""
schemas/responses.py

Response models for API endpoints.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class RadarChart(BaseModel):
    labels: list[str]
    keys: list[str]
    values: list[int]
    max: int = 100


class SafetyInfo(BaseModel):
    passed: bool
    hit_words_before: list[str]
    hit_words_after: list[str]


class MetaInfo(BaseModel):
    image_url: str
    duration_ms: int
    usage: Optional[dict[str, Any]] = None


class AnalyzeResponse(BaseModel):
    success: bool
    provider: str
    user_id: Optional[str] = None
    report: Optional[dict[str, Any]] = None
    radar_chart: Optional[RadarChart] = None
    mapped_project_directions: Optional[list[dict[str, Any]]] = None
    image_quality: Optional[dict[str, Any]] = None
    safety: Optional[SafetyInfo] = None
    meta: Optional[MetaInfo] = None
    message: Optional[str] = None
