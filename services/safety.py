"""
services/safety.py

Content safety and compliance checking service.

"""

import json
from typing import Any, Dict, List

from core.exceptions import SafetyCheckError


# ------------------------------------------------------------
# 1. Soft-sensitive words
# ------------------------------------------------------------
# These words are not ideal for user-facing medical-aesthetic copy,
# but can usually be rewritten into safer aesthetic wording.
#
# Example:
# "填充" -> "饱满度管理"
# "注射" -> "专业护理"
# "治疗" -> "专业护理"
#
# Note:
# We keep these out of HARD_FORBIDDEN_WORDS so that the report
# does not fail immediately when the model uses a fixable expression.
# ------------------------------------------------------------

SOFT_REPLACEMENTS: Dict[str, str] = {
    # Project / procedure-like wording
    "填充": "饱满度管理",
    "面部填充": "面部饱满度管理",
    "中面部填充": "中面部饱满度关注",
    "容量填充": "容量感管理",
    "注射": "专业护理",
    "手术": "专业方案",
    "整形": "美学调整方向",
    "处方": "建议方向",

    # Medical wording
    "治疗": "专业护理",
    "诊断": "专业观察",
    "病症": "状态表现",

    # Absolutist wording
    "完美": "协调",
    "最适合": "比较适合",
    "最美": "更有魅力",
    "必须": "可以考虑",
    "一定": "建议",

    # Anxiety-inducing wording
    "严重缺陷": "明显可优化方向",
    "缺陷": "可优化方向",
    "难看": "不够协调",
    "丑": "不够协调",
    "畸形": "比例不够协调",

    # Promise wording
    "根治": "长期关注",
    "治愈": "状态维护",
    "永久": "长期",
    "保证": "建议",
    "百分百": "较高程度",
    "100%": "较高程度",
}


# ------------------------------------------------------------
# 2. Hard-forbidden words
# ------------------------------------------------------------
# These are specific medical-aesthetic projects / drugs / devices
# or high-risk expressions. If they remain after soft replacement,
# the report should be blocked for manual review or regeneration.
#
# Important:
# "填充" is intentionally NOT here, because it can be safely rewritten.
# "手术/治疗/诊断/整形/处方" are also rewritten first as soft words.
# If you want stricter compliance, you can move them back here.
# ------------------------------------------------------------

HARD_FORBIDDEN_WORDS: List[str] = [
    "玻尿酸",
    "肉毒",
    "水光针",
    "超声炮",
    "热玛吉",
    "拉皮",
    "线雕",
    "瘦脸针",

    # Strong advertising / illegal promise risk
    "包有效",
    "包变美",
    "立刻见效",
    "马上见效",
    "年轻10岁",
    "年轻十岁",

    # Strong negative / anxiety-inducing wording
    "毁容",
    "失败脸",
]


# Kept for compatibility with old code naming.
# It now means: all words we care about before rewriting.
FORBIDDEN_WORDS: List[str] = list(SOFT_REPLACEMENTS.keys()) + HARD_FORBIDDEN_WORDS


class SafetyService:
    """Content safety checking and sanitization."""

    def _find_words(self, text: str, words: List[str]) -> List[str]:
        """Return unique words that appear in text, preserving configured order."""
        return [w for w in words if w in text]

    def _dump_report(self, report: Dict[str, Any]) -> str:
        """Serialize report safely for text checking."""
        return json.dumps(report, ensure_ascii=False)

    def check(self, text: str) -> Dict[str, Any]:
        """
        Check text for all monitored words.

        This method keeps backward-compatible output:
        {
            "passed": bool,
            "hit_words": [...]
        }

        It also returns soft/hard details:
        {
            "hit_soft_words": [...],
            "hit_hard_words": [...]
        }
        """
        hit_soft_words = self._find_words(text, list(SOFT_REPLACEMENTS.keys()))
        hit_hard_words = self._find_words(text, HARD_FORBIDDEN_WORDS)
        hit_words = hit_soft_words + hit_hard_words

        return {
            "passed": len(hit_words) == 0,
            "hit_words": hit_words,
            "hit_soft_words": hit_soft_words,
            "hit_hard_words": hit_hard_words,
        }

    def sanitize_text(self, text: str) -> str:
        """
        Replace soft-sensitive words with safer alternatives.

        Replacement order matters. Longer phrases should be replaced before
        shorter words to avoid partial replacement issues.
        """
        # Sort by length descending, e.g. "中面部填充" before "填充"
        for old in sorted(SOFT_REPLACEMENTS.keys(), key=len, reverse=True):
            new = SOFT_REPLACEMENTS[old]
            text = text.replace(old, new)
        return text

    def sanitize_json_obj(self, obj: Any) -> Any:
        """
        Recursively sanitize a JSON-like object.

        This is safer than converting the entire report to a string and
        replacing inside JSON text, because it avoids accidentally changing
        key names or breaking JSON structure.
        """
        if isinstance(obj, dict):
            return {k: self.sanitize_json_obj(v) for k, v in obj.items()}

        if isinstance(obj, list):
            return [self.sanitize_json_obj(v) for v in obj]

        if isinstance(obj, str):
            return self.sanitize_text(obj)

        return obj

    def sanitize(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Replace soft-sensitive words with safe alternatives.

        This method returns a new sanitized report object.
        """
        fixed = self.sanitize_json_obj(report)

        # Keep original fallback behavior in case unexpected object type appears.
        if isinstance(fixed, dict):
            return fixed

        return report

    def pipeline(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Full safety pipeline:
        1. Check original report.
        2. Sanitize soft-sensitive words.
        3. Re-check sanitized report.
        4. If only soft words were fixed, return success.
        5. If hard-forbidden words remain, raise SafetyCheckError.

        Returns:
            {
                "passed": True,
                "report": fixed_report,
                "hit_words_before": [...],
                "hit_words_after": [...],
                "hit_soft_words_before": [...],
                "hit_hard_words_before": [...],
                "hit_soft_words_after": [...],
                "hit_hard_words_after": [...]
            }
        """
        before_text = self._dump_report(report)
        before = self.check(before_text)

        # If no monitored words appear, pass directly.
        if before["passed"]:
            return {
                "passed": True,
                "report": report,
                "hit_words_before": [],
                "hit_words_after": [],
                "hit_soft_words_before": [],
                "hit_hard_words_before": [],
                "hit_soft_words_after": [],
                "hit_hard_words_after": [],
            }

        # Rewrite soft-sensitive words.
        fixed_report = self.sanitize(report)

        after_text = self._dump_report(fixed_report)
        after = self.check(after_text)

        # If hard-forbidden words still exist, block.
        # This means specific project/device/drug or high-risk wording remains.
        if after["hit_hard_words"]:
            raise SafetyCheckError(
                message="报告命中高风险敏感词，建议进入人工审核或重新生成。",
                hit_words=after["hit_hard_words"],
            )

        # If soft words still exist after replacement, block.
        # This usually means replacement dictionary missed some expression.
        if after["hit_soft_words"]:
            raise SafetyCheckError(
                message="报告命中敏感词，建议进入人工审核或重新生成。",
                hit_words=after["hit_soft_words"],
            )

        return {
            "passed": True,
            "report": fixed_report,
            "hit_words_before": before["hit_words"],
            "hit_words_after": after["hit_words"],
            "hit_soft_words_before": before["hit_soft_words"],
            "hit_hard_words_before": before["hit_hard_words"],
            "hit_soft_words_after": after["hit_soft_words"],
            "hit_hard_words_after": after["hit_hard_words"],
        }