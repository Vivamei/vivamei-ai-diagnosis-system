#!/usr/bin/env python
"""维护 sensitive_words.txt：合并新词、去重、按 Unicode 序排序。

Usage:
    python scripts/init_sensitive_words.py add "新词1" "新词2"
    python scripts/init_sensitive_words.py list
    python scripts/init_sensitive_words.py remove "旧词1"
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "apps" / "api" / "app" / "data" / "sensitive_words.txt"


def load() -> tuple[list[str], set[str]]:
    """返回 (注释/空行原序, 词集合)。"""
    if not FILE.exists():
        return [], set()
    lines = FILE.read_text(encoding="utf-8").splitlines()
    comments = [l for l in lines if l.strip().startswith("#") or not l.strip()]
    words = {
        l.strip()
        for l in lines
        if l.strip() and not l.strip().startswith("#")
    }
    return comments, words


def save(comments: list[str], words: set[str]) -> None:
    body = "\n".join(comments + sorted(words)) + "\n"
    FILE.write_text(body, encoding="utf-8")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    comments, words = load()
    if cmd == "list":
        for w in sorted(words):
            print(w)
    elif cmd == "add":
        before = len(words)
        words.update(w for w in sys.argv[2:] if w.strip())
        save(comments, words)
        print(f"added {len(words) - before} new words, total {len(words)}")
    elif cmd == "remove":
        before = len(words)
        for w in sys.argv[2:]:
            words.discard(w)
        save(comments, words)
        print(f"removed {before - len(words)} words, total {len(words)}")
    else:
        print(f"unknown cmd: {cmd}")
        sys.exit(2)


if __name__ == "__main__":
    main()
