"""
domain/radar.py

4S radar chart data normalization and report structure fallback.
Pure domain logic — no I/O, no dependencies.
"""

from __future__ import annotations

from typing import Any


def clamp_score(value: Any, default: int = 75) -> int:
    """Normalize any input to 0-100 integer."""
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        score = default
    return max(0, min(100, score))


def clamp_confidence(value: Any, default: float = 0.75) -> float:
    """Normalize any input to 0.0-1.0 confidence."""
    try:
        conf = float(value)
    except (TypeError, ValueError):
        conf = default
    return max(0.0, min(1.0, round(conf, 2)))


def default_zones() -> list[dict[str, str]]:
    return [
        {"zone": "额部", "status": "额部状态需结合清晰正面照进一步观察。", "strength": "整体观感较自然。", "optimization": "可关注额部清爽度与发际线协调感。"},
        {"zone": "眉眼", "status": "眉眼区域是面部表达的重要视觉中心。", "strength": "有助于形成个人气质记忆点。", "optimization": "可关注眉眼清晰度与眼周状态。"},
        {"zone": "中面部", "status": "中面部影响亲和力与年轻态观感。", "strength": "整体比例较自然。", "optimization": "可关注面中部饱满度与过渡流畅度。"},
        {"zone": "鼻部", "status": "鼻部影响面部立体感与中轴协调。", "strength": "整体观感较协调。", "optimization": "可关注鼻部与中面部的整体平衡。"},
        {"zone": "唇部", "status": "唇部影响气色与柔和度表达。", "strength": "有助于提升整体亲和力。", "optimization": "可关注唇色、唇形与妆造匹配。"},
        {"zone": "下颌轮廓", "status": "下颌轮廓影响脸部线条清晰度。", "strength": "整体线条具备自然感。", "optimization": "可关注轮廓线条的利落感与协调度。"},
    ]


def default_layers() -> list[dict[str, Any]]:
    return [
        {"layer": "皮肤层", "score": 75, "status": "皮肤层状态建议结合清晰光线进一步观察。", "optimization": "可关注肤色均匀度与清透感。"},
        {"layer": "皮下组织层", "score": 75, "status": "皮下组织层影响面部饱满度与柔和感。", "optimization": "可关注面部饱满度与自然过渡。"},
        {"layer": "筋膜支撑层", "score": 75, "status": "筋膜支撑层影响面部紧致感与线条走向。", "optimization": "可关注整体紧致感与疲惫感管理。"},
        {"layer": "骨骼轮廓层", "score": 75, "status": "骨骼轮廓层影响脸部框架与风格辨识度。", "optimization": "可关注轮廓协调与整体比例。"},
    ]


def ensure_list(value: Any, default: list[Any], limit: int | None = None) -> list[Any]:
    if isinstance(value, list):
        items = value
    elif value is None:
        items = default
    else:
        items = [value]
    if limit is not None:
        items = items[:limit]
    return items


def normalize_4s_report(report: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize 4S report structure.
    Ensures all required fields exist with safe defaults.
    """
    report.setdefault("report_type", "4S 美学报告")

    # 1. Stype
    stype = report.get("stype") if isinstance(report.get("stype"), dict) else {}
    stype.setdefault("dimension_name", "分相 Stype")
    stype.setdefault("label", "复合型")
    stype["score"] = clamp_score(stype.get("score", report.get("stype_score", 75)))
    stype["confidence"] = clamp_confidence(stype.get("confidence", 0.75))
    stype.setdefault("description", "整体相型呈复合特征，建议结合清晰正面照与动态表情进一步确认。")
    stype["evidence"] = ensure_list(stype.get("evidence"), ["整体轮廓", "面部饱满度", "皮肤质感"], limit=3)
    report["stype"] = stype

    # 2. Style
    style = report.get("style") if isinstance(report.get("style"), dict) else {}
    style.setdefault("dimension_name", "分型 Style")
    style.setdefault("label", report.get("style_tag", "自然亲和"))
    style["score"] = clamp_score(style.get("score", report.get("style_score", 78)))
    style["confidence"] = clamp_confidence(style.get("confidence", report.get("style_confidence", 0.78)))
    style.setdefault("description", "整体气质自然亲和，适合以协调、干净、耐看的方向强化个人特色。")
    style["keywords"] = ensure_list(style.get("keywords"), ["自然", "亲和", "协调"], limit=4)
    report["style"] = style

    # 3. Subzone
    subzone = report.get("subzone") if isinstance(report.get("subzone"), dict) else {}
    subzone.setdefault("dimension_name", "分区 Subzone")
    subzone["score"] = clamp_score(subzone.get("score", report.get("subzone_score", 76)))
    subzone.setdefault("summary", "面部各分区整体协调度较自然，可重点关注眉眼、中面部与轮廓线条的统一感。")
    subzone["zones"] = ensure_list(subzone.get("zones"), default_zones(), limit=6)
    filled_zones = []
    for i, zone in enumerate(subzone["zones"]):
        if not isinstance(zone, dict):
            zone = {}
        default = default_zones()[min(i, 5)]
        zone.setdefault("zone", default["zone"])
        zone.setdefault("status", default["status"])
        zone.setdefault("strength", default["strength"])
        zone.setdefault("optimization", default["optimization"])
        filled_zones.append(zone)
    subzone["zones"] = filled_zones
    report["subzone"] = subzone

    # 4. Struct
    struct = report.get("struct") if isinstance(report.get("struct"), dict) else {}
    struct.setdefault("dimension_name", "分层 Struct")
    struct["score"] = clamp_score(struct.get("score", report.get("struct_score", 75)))
    struct.setdefault("summary", "结构层次整体以自然协调为主，可从肤质、饱满度、紧致感和轮廓协调度综合优化。")
    struct["layers"] = ensure_list(struct.get("layers"), default_layers(), limit=4)
    filled_layers = []
    for i, layer in enumerate(struct["layers"]):
        if not isinstance(layer, dict):
            layer = {}
        default = default_layers()[min(i, 3)]
        layer.setdefault("layer", default["layer"])
        layer["score"] = clamp_score(layer.get("score", default["score"]))
        layer.setdefault("status", default["status"])
        layer.setdefault("optimization", default["optimization"])
        filled_layers.append(layer)
    struct["layers"] = filled_layers
    report["struct"] = struct

    # 5. Radar scores
    radar_scores = report.get("radar_scores") if isinstance(report.get("radar_scores"), dict) else {}
    radar_scores = {
        "stype": clamp_score(radar_scores.get("stype", stype["score"])),
        "style": clamp_score(radar_scores.get("style", style["score"])),
        "subzone": clamp_score(radar_scores.get("subzone", subzone["score"])),
        "struct": clamp_score(radar_scores.get("struct", struct["score"])),
    }
    report["radar_scores"] = radar_scores
    report["radar_chart"] = {
        "labels": ["分相 Stype", "分型 Style", "分区 Subzone", "分层 Struct"],
        "keys": ["stype", "style", "subzone", "struct"],
        "values": [radar_scores["stype"], radar_scores["style"], radar_scores["subzone"], radar_scores["struct"]],
        "max": 100,
    }

    # 6. Aesthetic optimization
    aesthetic_opt = report.get("aesthetic_optimization") if isinstance(report.get("aesthetic_optimization"), dict) else {}
    aesthetic_opt.setdefault("summary", "建议围绕4S结果，以自然协调、扬长避短为核心，优先关注肤质、分区协调和轮廓线条的整体统一感。")
    aesthetic_opt["directions"] = ensure_list(
        aesthetic_opt.get("directions"),
        ["优先关注肤质清透感与气色管理。", "关注面部各分区的协调过渡。", "结合个人气质强化自然耐看的风格。"],
        limit=4,
    )
    report["aesthetic_optimization"] = aesthetic_opt

    # 7. Project directions, CTA, disclaimer
    report["project_directions"] = ensure_list(
        report.get("project_directions"),
        ["肤质管理", "分区协调", "轮廓精致"],
        limit=4,
    )
    report.setdefault("lead_cta", {
        "title": "领取你的专属4S美学方案",
        "text": "填写信息后，专业顾问将结合你的4S报告，为你提供一对一美学建议。",
        "button": "立即领取福利",
    })
    report.setdefault("disclaimer", "本报告由 AI 生成，仅作为美学体验参考，不作为专业医疗意见、处置依据或效果承诺。")

    return report
