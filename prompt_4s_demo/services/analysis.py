"""
services/analysis.py

Analysis orchestration service.
Coordinates image processing, LLM calling, safety checks, and project mapping.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from core.config import Settings
from domain.project_mapping import map_project_directions
from services.image import ImageService
from services.llm import LLMService
from services.safety import SafetyService

logger = logging.getLogger(__name__)


class AnalysisService:
    """Orchestrates the full 4S analysis pipeline."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.image_service = ImageService(settings)
        self.llm_service = LLMService(settings)
        self.safety_service = SafetyService()

    def analyze_file(self, file, user_id: str | None = None) -> dict[str, Any]:
        """Analyze an uploaded file and return the full report."""
        # 1. Save uploaded file
        image_path = self.image_service.save_upload(file)
        logger.info("Saved uploaded image: %s", image_path.name)

        # 2. Validate image quality
        quality = self.image_service.validate_quality(image_path)
        if not quality["passed"]:
            return {
                "success": False,
                "provider": self.settings.llm_provider,
                "user_id": user_id,
                "message": "图片质量不满足分析要求，请重新上传。",
                "image_quality": quality,
            }

        # 3. Get image URL
        image_url = self.image_service.build_public_url(image_path)

        # 4. Generate report via LLM
        llm_result = self.llm_service.generate_report(image_url)
        report = llm_result["report"]

        # 5. Safety pipeline
        safety_result = self.safety_service.pipeline(report)
        safe_report = safety_result["report"]

        # 6. Project direction mapping
        mapped_projects = map_project_directions(
            safe_report.get("project_directions", [])
        )

        # 7. Build response
        return self._build_response(
            safe_report=safe_report,
            safety_result=safety_result,
            mapped_projects=mapped_projects,
            image_url=image_url,
            quality=quality,
            user_id=user_id,
            duration_ms=llm_result["duration_ms"],
            usage=llm_result["usage"],
        )

    def analyze_url(self, image_url: str, user_id: str | None = None) -> dict[str, Any]:
        """Analyze an image via public URL and return the full report."""
        logger.info("Analyzing image URL: %s", image_url)

        # 1. Generate report via LLM
        llm_result = self.llm_service.generate_report(image_url)
        report = llm_result["report"]

        # 2. Safety pipeline
        safety_result = self.safety_service.pipeline(report)
        safe_report = safety_result["report"]

        # 3. Project direction mapping
        mapped_projects = map_project_directions(
            safe_report.get("project_directions", [])
        )

        # 4. Build response
        return self._build_response(
            safe_report=safe_report,
            safety_result=safety_result,
            mapped_projects=mapped_projects,
            image_url=image_url,
            quality=None,
            user_id=user_id,
            duration_ms=llm_result["duration_ms"],
            usage=llm_result["usage"],
        )

    def _build_response(
        self,
        *,
        safe_report: dict[str, Any],
        safety_result: dict[str, Any],
        mapped_projects: list[dict[str, Any]],
        image_url: str,
        quality: dict[str, Any] | None,
        user_id: str | None,
        duration_ms: int,
        usage: Any,
    ) -> dict[str, Any]:
        """Build the final API response."""
        radar_chart = safe_report.get("radar_chart", {})
        return {
            "success": True,
            "provider": self.settings.llm_provider,
            "user_id": user_id,
            "image_quality": quality,
            "report": safe_report,
            "radar_chart": radar_chart,
            "mapped_project_directions": mapped_projects,
            "safety": {
                "passed": True,
                "hit_words_before": safety_result["hit_words_before"],
                "hit_words_after": safety_result["hit_words_after"],
            },
            "meta": {
                "image_url": image_url,
                "duration_ms": duration_ms,
                "usage": usage,
            },
        }
