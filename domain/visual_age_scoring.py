"""Deterministic, server-internal visual-age calibration for V4 scores."""

from __future__ import annotations

from copy import deepcopy
import math
import re
from typing import Any, Dict, Optional, Tuple


AGE_BASE_SCORES = {
    "18-24": 100,
    "24-30": 95,
    "30-35": 90,
    "36-40": 85,
    "41-45": 80,
    "46-50": 75,
    "51-55": 70,
    "56-60": 68,
    "61-65": 66,
    "66-70": 64,
    "71-75": 62,
    "76-80": 60,
    "81-85": 60,
    "86-90": 60,
    "91-95": 60,
    "96-100": 60,
}

AGE_SENSITIVE_DIMENSIONS = ("stype", "subzone", "struct")


def _finite_number(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _normalize_age_range(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    normalized = re.sub(r"\s+", "", value.strip())
    normalized = re.sub(r"[~～—–至]", "-", normalized)
    match = re.fullmatch(r"(\d{1,3})-(\d{1,3})", normalized)
    if not match:
        return None
    return f"{int(match.group(1))}-{int(match.group(2))}"


def age_base_score(age_range: Any) -> Optional[int]:
    """Return the workbook base score for an exact supported age band."""
    normalized = _normalize_age_range(age_range)
    return AGE_BASE_SCORES.get(normalized) if normalized else None


def confidence_weight(confidence: Any) -> float:
    """Map a model confidence to the approved capped calibration weight."""
    number = _finite_number(confidence)
    if number is None or number < 0.55:
        return 0.0
    if number < 0.70:
        return 0.15
    if number < 0.85:
        return 0.30
    return 0.45


def _valid_evidence_points(items: Any) -> int:
    if not isinstance(items, list):
        return 0

    seen = set()
    total = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        tag = item.get("tag")
        evidence = item.get("evidence")
        points = _finite_number(item.get("points"))
        if (
            not isinstance(tag, str)
            or not tag.strip()
            or not isinstance(evidence, str)
            or not evidence.strip()
            or points is None
            or points < 1
            or points > 10
        ):
            continue
        normalized_tag = re.sub(r"\s+", "", tag).casefold()
        if normalized_tag in seen:
            continue
        seen.add(normalized_tag)
        total += int(round(points))
    return total


def _evidence_adjustment(score_evidence: Any, dimension: str) -> int:
    if not isinstance(score_evidence, dict):
        return 0
    dimension_evidence = score_evidence.get(dimension)
    if not isinstance(dimension_evidence, dict):
        return 0
    positive = _valid_evidence_points(dimension_evidence.get("positive"))
    negative = _valid_evidence_points(dimension_evidence.get("negative"))
    return max(-10, min(10, positive - negative))


def calibrate_report_scores(
    report: Dict[str, Any],
    assessment: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Calibrate three state scores and return a private audit summary.

    The input is never mutated. Style is deliberately excluded because the
    supplied workbook assigns it the same base score for every age band.
    """
    calibrated = deepcopy(report)
    if not isinstance(assessment, dict):
        return calibrated, {"applied": False, "reason": "missing_assessment"}

    base_score = age_base_score(assessment.get("visual_age_range"))
    if base_score is None:
        return calibrated, {"applied": False, "reason": "invalid_age_range"}

    weight = confidence_weight(assessment.get("visual_age_confidence"))
    if weight == 0:
        return calibrated, {"applied": False, "reason": "low_confidence"}

    audit: Dict[str, Any] = {
        "applied": True,
        "age_range": _normalize_age_range(assessment.get("visual_age_range")),
        "confidence": _finite_number(assessment.get("visual_age_confidence")),
        "weight": weight,
        "dimensions": {},
    }
    score_evidence = assessment.get("score_evidence")

    for dimension in AGE_SENSITIVE_DIMENSIONS:
        payload = calibrated.get(dimension)
        raw_score = (
            _finite_number(payload.get("score"))
            if isinstance(payload, dict)
            else None
        )
        if raw_score is None:
            audit["dimensions"][dimension] = {"skipped": "invalid_raw_score"}
            continue

        adjustment = _evidence_adjustment(score_evidence, dimension)
        candidate = max(60, min(100, base_score + adjustment))
        blended = round(raw_score * (1 - weight) + candidate * weight)
        lower = max(0, round(raw_score) - 10)
        upper = min(100, round(raw_score) + 10)
        final_score = max(lower, min(upper, blended))
        payload["score"] = final_score
        audit["dimensions"][dimension] = {
            "raw_score": raw_score,
            "age_base_score": base_score,
            "evidence_adjustment": adjustment,
            "candidate_score": candidate,
            "final_score": final_score,
            "delta": final_score - raw_score,
        }

    return calibrated, audit
