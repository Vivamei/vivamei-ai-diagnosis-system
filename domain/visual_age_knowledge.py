"""Curated, observable-only signals adapted from the supplied workbook."""

from __future__ import annotations


POSITIVE_SIGNALS = {
    "skin": (
        "均匀肤色",
        "透亮好气色",
        "细腻肌理",
        "平滑肤质",
        "紧致弹润",
        "光泽均匀",
        "毛孔细腻",
        "无明显细纹",
    ),
    "soft_tissue": (
        "轮廓清晰",
        "皮肉贴合",
        "紧致苹果肌",
        "平整泪沟",
        "饱满太阳穴",
        "软组织匀称",
        "下颌缘清晰",
        "无明显下垂",
    ),
    "structure": (
        "面部线条流畅",
        "三庭均衡",
        "五官协调",
        "轮廓支撑清晰",
        "面中过渡自然",
        "颌面线条平整",
    ),
}

NEGATIVE_SIGNALS = {
    "skin": (
        "暗沉",
        "肤色不均",
        "毛孔粗大",
        "皮肤粗糙",
        "干纹",
        "细纹",
        "抬头纹",
        "鱼尾纹",
        "法令纹",
        "木偶纹",
    ),
    "soft_tissue": (
        "松弛",
        "下垂",
        "泪沟明显",
        "眼袋明显",
        "苹果肌下移",
        "太阳穴凹陷",
        "面中凹陷",
        "口角囊袋",
        "下颌缘模糊",
        "软组织堆积",
        "软组织容量缺失",
    ),
    "structure": (
        "轮廓模糊",
        "支撑感偏弱",
        "面部线条断层",
        "左右轮廓明显不对称",
    ),
}


def _format_group(title: str, values: dict) -> str:
    lines = [title]
    labels = {
        "skin": "皮肤可见信号",
        "soft_tissue": "软组织可见信号",
        "structure": "轮廓与支撑可见信号",
    }
    for key, items in values.items():
        lines.append(f"- {labels[key]}：{'、'.join(items)}")
    return "\n".join(lines)


def build_visual_age_knowledge_prompt() -> str:
    """Build a bounded safe prompt rather than injecting the raw medical list."""
    return "\n\n".join(
        [
            "【视觉年龄加减分观察词库】",
            _format_group("可作为加分证据的外观信号：", POSITIVE_SIGNALS),
            _format_group("可作为减分证据的外观信号：", NEGATIVE_SIGNALS),
            (
                "安全边界：只允许描述照片中可见的外观信号；"
                "不得诊断疾病，不得推断真实年龄，不评价健康状况。"
                "妆容、滤镜、光线造成的信号必须降低置信度。"
            ),
        ]
    )
