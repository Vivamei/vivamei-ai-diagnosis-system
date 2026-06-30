"""
services/safety.py

Content safety and compliance checking service.
"""

import json
from typing import Any

from core.exceptions import SafetyCheckError

# Forbidden words: avoid absolutist, diagnostic, anxiety-inducing, or project-specific expressions.
# Note: "老" is NOT forbidden because "衰老相型" is a client 4S term.
FORBIDDEN_WORDS = [
    "100%", "百分百", "永久", "根治", "治愈", "保证", "完美", "最",
    "必须", "一定", "丑", "难看", "畸形", "严重缺陷", "病症",
    "治疗", "诊断", "手术", "玻尿酸", "肉毒", "水光针", "超声炮",
    "热玛吉", "拉皮", "瘦脸针", "填充", "整形", "处方",
]

REPLACEMENTS = {
    "完美": "协调",
    "最适合": "比较适合",
    "最美": "更有魅力",
    "必须": "可以考虑",
    "一定": "建议",
    "严重缺陷": "明显可优化方向",
    "缺陷": "可优化方向",
    "治疗": "护理",
    "诊断": "观察",
    "难看": "不够协调",
    "手术": "专业方案",
    "整形": "美学调整方向",
    "处方": "建议方向",
}


class SafetyService:
    """Content safety checking and sanitization."""

    def check(self, text: str) -> dict[str, Any]:
        """Check text for forbidden words."""
        hit_words = [w for w in FORBIDDEN_WORDS if w in text]
        return {"passed": len(hit_words) == 0, "hit_words": hit_words}

    def sanitize(self, report: dict[str, Any]) -> dict[str, Any]:
        """Replace forbidden words with safe alternatives."""
        text = json.dumps(report, ensure_ascii=False)
        for old, new in REPLACEMENTS.items():
            text = text.replace(old, new)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return report

    def pipeline(self, report: dict[str, Any]) -> dict[str, Any]:
        """
        Full safety pipeline: check → sanitize → re-check.
        Returns sanitized report if possible, raises if still unsafe.
        """
        before = self.check(json.dumps(report, ensure_ascii=False))
        if before["passed"]:
            return {
                "passed": True,
                "report": report,
                "hit_words_before": [],
                "hit_words_after": [],
            }

        fixed_report = self.sanitize(report)
        after = self.check(json.dumps(fixed_report, ensure_ascii=False))

        if not after["passed"]:
            raise SafetyCheckError(
                message="报告命中敏感词，建议进入人工审核或重新生成。",
                hit_words=after["hit_words"],
            )

        return {
            "passed": True,
            "report": fixed_report,
            "hit_words_before": before["hit_words"],
            "hit_words_after": after["hit_words"],
        }
