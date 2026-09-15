"""V4 pipeline helpers for private face checks and score finalization."""

from __future__ import annotations

from copy import deepcopy
import logging
from typing import Any, Dict, List, Optional, Tuple

from core.exceptions import AppException
from domain.radar import normalize_4s_report
from domain.radar_semantics import build_state_gap_radar
from domain.visual_age_scoring import calibrate_report_scores
from utils.report_postprocess import validate_dynamic_scores
from utils.style_postprocess import apply_style_knowledge


logger = logging.getLogger(__name__)

def validate_face_assessment(
    assessment: Any,
) -> Optional[Dict[str, Any]]:
    """Reject unusable face inputs; tolerate absent metadata for compatibility."""
    if not isinstance(assessment, dict):
        return None

    face_detected = assessment.get("face_detected")
    try:
        face_count = int(assessment.get("face_count", 1))
    except (TypeError, ValueError):
        face_count = 1

    if face_detected is False or face_count <= 0:
        raise AppException(
            "未检测到清晰、完整的人脸，请重新上传正面人像照片。",
            status_code=422,
            code="FACE_NOT_DETECTED",
            retryable=False,
        )
    if face_count > 1:
        raise AppException(
            "检测到多张人脸，请上传只包含一人的正面照片。",
            status_code=422,
            code="MULTIPLE_FACES_DETECTED",
            retryable=False,
        )
    if str(assessment.get("image_quality", "")).strip().lower() == "poor":
        raise AppException(
            "人脸过小、模糊、遮挡或角度不适合分析，请重新上传清晰正面照片。",
            status_code=422,
            code="FACE_IMAGE_QUALITY_LOW",
            retryable=False,
        )
    return assessment


def public_style_result(style_result: Any) -> Dict[str, Any]:
    """Return first-stage diagnostics without private visual-age metadata."""
    if not isinstance(style_result, dict):
        return {}
    public = deepcopy(style_result)
    public.pop("face_assessment", None)
    for key in (
        "visual_age_range",
        "visual_age_confidence",
        "score_evidence",
    ):
        public.pop(key, None)
    return public


def _set_state_gap_radar(report: Dict[str, Any]) -> None:
    radar_scores, radar_chart = build_state_gap_radar(report)
    report["radar_scores"] = radar_scores
    report["radar_chart"] = radar_chart


def finalize_report(
    report: Dict[str, Any],
    final_style: str,
    assessment: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[str], Dict[str, Any]]:
    """Strictly validate, normalize, calibrate, and create normalized state-gap radar data."""
    report, score_warnings = validate_dynamic_scores(report)
    report = normalize_4s_report(report)

    if isinstance(report.get("style"), dict):
        report["style"]["label"] = final_style
        report["style"].pop("candidates", None)
        report["style"].pop("top3", None)
        report["style"].pop("style_top3", None)

    report = apply_style_knowledge(report, final_style)
    report, calibration_audit = calibrate_report_scores(report, assessment)
    _set_state_gap_radar(report)

    if calibration_audit.get("applied"):
        deltas = {
            key: value.get("delta")
            for key, value in calibration_audit.get("dimensions", {}).items()
            if isinstance(value, dict) and "delta" in value
        }
        logger.info(
            "Visual-age calibration range=%s confidence=%s weight=%s deltas=%s",
            calibration_audit.get("age_range"),
            calibration_audit.get("confidence"),
            calibration_audit.get("weight"),
            deltas,
        )
    else:
        logger.info(
            "Visual-age calibration skipped reason=%s",
            calibration_audit.get("reason"),
        )

    return report, score_warnings, calibration_audit
