"""敏感词过滤（M9 升级版）。

从 `app/data/sensitive_words.txt` 加载词库（缓存于 lru_cache），
对文本做正则匹配。支持运行时通过 CLI（scripts/init_sensitive_words.py）维护词库。
词库修改后需重启 API 服务以刷新缓存。
"""
import re
from functools import lru_cache
from pathlib import Path

_FILE = Path(__file__).resolve().parents[1] / "data" / "sensitive_words.txt"


@lru_cache(maxsize=1)
def _words() -> list[str]:
    if not _FILE.exists():
        return []
    return [
        w.strip()
        for w in _FILE.read_text(encoding="utf-8").splitlines()
        if w.strip() and not w.strip().startswith("#")
    ]


@lru_cache(maxsize=1)
def _pattern() -> re.Pattern[str]:
    words = _words()
    if not words:
        return re.compile(r"$.^")  # 永远不匹配
    return re.compile("|".join(map(re.escape, words)))


def contains_banned(text: str) -> bool:
    if not text:
        return False
    return bool(_pattern().search(text))
