"""Strict V4 validation and score/radar synchronization."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import re

from core.exceptions import LLMCallError
from domain.radar_semantics import build_state_gap_radar


DIMENSIONS = ("stype", "style", "subzone", "struct")


def _clamp_score(value: int) -> int:
    return max(0, min(100, int(value)))


def _parse_score(value: Any, default: Optional[int] = None) -> Optional[int]:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return _clamp_score(value)
    if isinstance(value, float):
        return _clamp_score(round(value))
    if isinstance(value, str):
        match = re.search(r"\d+(\.\d+)?", value)
        if match:
            return _clamp_score(round(float(match.group(0))))
    return default


def _parse_confidence(value: Any, default: float = 0.80) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if parsed > 1:
        parsed /= 100.0
    return max(0.0, min(1.0, round(parsed, 2)))


def _avg_int(values: List[int]) -> Optional[int]:
    return int(round(sum(values) / len(values))) if values else None


def _invalid_scores_error(missing_dimensions: List[str]) -> LLMCallError:
    return LLMCallError(
        "4S 分析缺少有效维度分数，请稍后重试。",
        code="LLM_INVALID_RESPONSE",
        status_code=502,
        retryable=True,
        details={"missing_dimensions": missing_dimensions},
    )


def _require_dimension_scores(report: Dict[str, Any]) -> None:
    missing = []
    for dimension in DIMENSIONS:
        section = report.get(dimension)
        score = (
            _parse_score(section.get("score"), default=None)
            if isinstance(section, dict)
            else None
        )
        if score is None:
            missing.append(dimension)
    if missing:
        raise _invalid_scores_error(missing)


def _sync_radar_scores(report: Dict[str, Any]) -> None:
    radar_scores, radar_chart = build_state_gap_radar(report)
    report["radar_scores"] = radar_scores
    report["radar_chart"] = radar_chart


def _average_children(
    section: Dict[str, Any],
    *,
    section_name: str,
    child_key: str,
    warnings: List[str],
) -> None:
    children = section.get(child_key)
    if not isinstance(children, list):
        warnings.append(
            f"{section_name}.{child_key} 缺失或不是 list，保留 {section_name}.score"
        )
        return

    valid_scores: List[int] = []
    invalid_count = 0
    for child in children:
        if not isinstance(child, dict):
            invalid_count += 1
            continue
        parsed = _parse_score(child.get("score"), default=None)
        if parsed is None:
            invalid_count += 1
            continue
        child["score"] = parsed
        valid_scores.append(parsed)

    if invalid_count:
        warnings.append(
            f"{section_name}.{child_key} 忽略 {invalid_count} 个无效 score"
        )

    average = _avg_int(valid_scores)
    if average is None:
        warnings.append(
            f"{section_name}.{child_key} 没有有效 score，保留 {section_name}.score"
        )
        return

    old_score = _parse_score(section.get("score"), default=None)
    if old_score is None or abs(old_score - average) > 3:
        warnings.append(
            f"{section_name}.score 已由 {old_score} 修正为 {average}"
        )
    section["score"] = average


def validate_dynamic_scores(
    report: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    """Validate four state scores without fabricating missing values."""
    if not isinstance(report, dict):
        raise _invalid_scores_error(list(DIMENSIONS))

    _require_dimension_scores(report)
    warnings: List[str] = []

    for section_name in ("stype", "style"):
        section = report[section_name]
        section["score"] = _parse_score(section["score"], default=None)
        section["confidence"] = _parse_confidence(
            section.get("confidence"),
            default=0.80,
        )

    subzone = report["subzone"]
    subzone["score"] = _parse_score(subzone["score"], default=None)
    _average_children(
        subzone,
        section_name="subzone",
        child_key="zones",
        warnings=warnings,
    )

    struct = report["struct"]
    struct["score"] = _parse_score(struct["score"], default=None)
    _average_children(
        struct,
        section_name="struct",
        child_key="layers",
        warnings=warnings,
    )

    scores = [report[name]["score"] for name in DIMENSIONS]
    if scores == [82, 84, 80, 78]:
        warnings.append("检测到疑似模板固定分数 82/84/80/78")

    _sync_radar_scores(report)
    return report, warnings
