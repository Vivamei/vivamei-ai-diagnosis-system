"""Canonical mapping from 4S state scores to radar display indexes."""

from __future__ import annotations

from typing import Any, Dict, Tuple


DIMENSIONS = ("stype", "style", "subzone", "struct")
LABELS = ("分相 Stype", "分型 Style", "分区 Subzone", "分层 Struct")


def _clamp_state_score(value: Any) -> int:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid state score: {value!r}") from exc
    return max(0, min(100, score))


def state_gap_index(state_score: Any) -> int:
    """Normalize the designed 60–100 state band to a 0–100 gap index.

    Scores below 60 remain capped at 100. Adding 0.5 gives predictable
    half-up rounding, avoiding Python's banker's rounding at values like 52.5.
    """
    score = _clamp_state_score(state_score)
    normalized = int((100 - score) * 2.5 + 0.5)
    return max(0, min(100, normalized))


def radar_value(dimension: str, state_score: Any) -> int:
    """Return the approved radar value for one 4S dimension."""
    score = _clamp_state_score(state_score)
    if dimension == "style":
        return score
    return state_gap_index(score)


def build_state_gap_radar(
    report: Dict[str, Any],
) -> Tuple[Dict[str, int], Dict[str, Any]]:
    """Build the only public radar representation."""
    state_scores = {
        dimension: _clamp_state_score(report[dimension]["score"])
        for dimension in DIMENSIONS
    }
    radar_scores = {
        dimension: radar_value(dimension, state_scores[dimension])
        for dimension in DIMENSIONS
    }
    radar_chart = {
        "labels": list(LABELS),
        "keys": list(DIMENSIONS),
        "state_values": [state_scores[key] for key in DIMENSIONS],
        "values": [radar_scores[key] for key in DIMENSIONS],
        "max": 100,
        "semantics": "four_s_state_gap_index",
    }
    return radar_scores, radar_chart
