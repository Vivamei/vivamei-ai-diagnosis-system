"""
domain/project_mapping.py

Maps 4S aesthetic directions to safe, client-facing descriptions.
Pure domain data — no I/O.
"""

from __future__ import annotations

from typing import Any

PROJECT_DIRECTION_MAP: dict[str, dict[str, str]] = {
    "肤质管理": {
        "display_title": "肤质清透感管理",
        "safe_description": "可以关注肤色均匀度、清透感和日常保养，让整体状态看起来更干净、更有精神。",
        "consult_note": "具体护理方式建议到院后由专业顾问结合皮肤状态确认。",
    },
    "轮廓精致": {
        "display_title": "轮廓线条精致感",
        "safe_description": "可以关注面部线条的清晰度和协调感，让整体气质更利落、更有精神。",
        "consult_note": "具体改善方向建议结合正面、侧面和动态表情综合判断。",
    },
    "年轻态维护": {
        "display_title": "年轻态与紧致感维护",
        "safe_description": "可以关注整体疲惫感、紧致感和面部状态管理，让气质更明亮自然。",
        "consult_note": "具体方案需要结合年龄、皮肤状态和个人诉求进一步确认。",
    },
    "眉眼精致": {
        "display_title": "眉眼清晰度提升",
        "safe_description": "可以关注眉眼区域的清晰度、眼周状态和妆造细节，让面部重点更明确。",
        "consult_note": "建议结合妆容、眉形和眼周状态进行综合设计。",
    },
    "面部协调": {
        "display_title": "面部比例协调感",
        "safe_description": "可以关注整体五官比例和风格统一感，让原有优势更自然地呈现。",
        "consult_note": "建议由专业顾问结合面诊沟通提供个性化建议。",
    },
    "气质妆造": {
        "display_title": "气质妆造优化",
        "safe_description": "可以通过妆容、眉形、唇色和穿搭风格强化当前美学气质。",
        "consult_note": "适合先从低门槛的妆造建议开始优化整体氛围。",
    },
    "发型优化": {
        "display_title": "发型与脸部风格匹配",
        "safe_description": "可以通过发型层次、刘海和发色调整，让脸部比例和整体风格更协调。",
        "consult_note": "建议结合脸型、发量和日常风格进行选择。",
    },
    "容量饱满度": {
        "display_title": "面部饱满度与过渡感",
        "safe_description": "可以关注面中部、苹果肌和太阳穴等区域的整体饱满度与自然过渡。",
        "consult_note": "具体方向建议结合正面、侧面和动态表情综合判断。",
    },
    "结构支撑": {
        "display_title": "结构支撑与紧致感",
        "safe_description": "可以关注面部支撑感、线条走向和整体紧致状态，让轮廓更清爽。",
        "consult_note": "建议到院后结合面部层次状态进行专业沟通。",
    },
    "分区协调": {
        "display_title": "面部分区协调优化",
        "safe_description": "可以关注额部、眉眼、中面部、鼻唇和下颌之间的整体协调关系。",
        "consult_note": "适合结合4S分区报告进行个性化沟通。",
    },
}


def map_project_directions(directions: list[str]) -> list[dict[str, Any]]:
    """Map model output directions to safe, display-ready recommendations."""
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    for direction in directions:
        if not direction or direction in seen:
            continue
        seen.add(direction)
        item = PROJECT_DIRECTION_MAP.get(direction)
        if item:
            results.append({"direction": direction, **item})
        else:
            results.append({
                "direction": direction,
                "display_title": "个性化美学方向",
                "safe_description": "可以结合个人气质、面部状态和实际诉求，进一步确认更适合自己的美学优化方向。",
                "consult_note": "具体建议请以到院专业沟通为准。",
            })

    return results
