"""Deterministic postprocessing for style-specific report content."""

from copy import deepcopy
from typing import Any, Dict, Iterable, List

from domain.aesthetic_knowledge import STYLE_KNOWLEDGE, build_style_reference


def _lowest(items: Iterable[Any], *, threshold: int, limit: int) -> List[dict]:
    valid = [
        item
        for item in items
        if isinstance(item, dict) and item.get("score", 100) < threshold
    ]
    return sorted(valid, key=lambda item: item.get("score", 100))[:limit]


def _append_unique(target: List[str], text: Any) -> None:
    value = str(text or "").strip()
    if value and value not in target:
        target.append(value)


def apply_style_knowledge(
    report: Dict[str, Any], final_style: str
) -> Dict[str, Any]:
    """Apply authoritative composition and differentiated safe directions."""
    result = deepcopy(report) if isinstance(report, dict) else {}
    knowledge = STYLE_KNOWLEDGE.get(final_style, {})

    style = result.setdefault("style", {})
    if not isinstance(style, dict):
        style = {}
        result["style"] = style
    style["label"] = final_style

    stype = result.setdefault("stype", {})
    if not isinstance(stype, dict):
        stype = {}
        result["stype"] = stype
    stype["style_reference"] = build_style_reference(final_style)
    aging_signals = stype.get("aging_signals")
    if not isinstance(aging_signals, dict):
        aging_signals = {}
    stype["aging_signals"] = {
        key: value if isinstance(value, list) else []
        for key, value in {
            "skin": aging_signals.get("skin", []),
            "soft_tissue": aging_signals.get("soft_tissue", []),
            "bone": aging_signals.get("bone", []),
        }.items()
    }

    directions: List[str] = []
    first_feature = knowledge.get("first_feature", "")
    if first_feature:
        _append_unique(directions, f"围绕{first_feature}维护本型核心辨识度")

    subzone = result.get("subzone", {})
    zones = subzone.get("zones", []) if isinstance(subzone, dict) else []
    zone_map = knowledge.get("zone_directions", {})
    low_zones = _lowest(zones, threshold=80, limit=2)
    for zone in low_zones:
        text = zone_map.get(zone.get("zone"))
        if text:
            zone["optimization"] = text
            _append_unique(directions, text)

    struct = result.get("struct", {})
    layers = struct.get("layers", []) if isinstance(struct, dict) else []
    for layer in _lowest(layers, threshold=78, limit=2):
        _append_unique(directions, layer.get("optimization"))

    for text in knowledge.get("priority_safe_directions", []):
        _append_unique(directions, text)
        if len(directions) >= 4:
            break

    result["aesthetic_optimization"] = {
        "summary": f"围绕{final_style}气质，结合照片可见分区状态进行协调维护。",
        "directions": directions[:4],
    }
    result["project_directions"] = knowledge.get("priority_directions", [])[:4]
    return result
