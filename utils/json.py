"""
utils/json.py
JSON extraction utilities with robust error handling for production.
"""
import json
import re
from typing import Dict, Any, Optional, List
import logging

# 配置日志
logger = logging.getLogger(__name__)


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Extract JSON from LLM response text with comprehensive error handling.
    Returns valid JSON dict or raises ValueError with user-friendly message.
    """
    if not text or not text.strip():
        raise ValueError("LLM返回内容为空，请重试")

    raw = text.strip()

    # Step 1: 移除markdown代码块标记
    raw = _remove_markdown_blocks(raw)

    # Step 2: 尝试直接解析（最快速）
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.debug("直接解析JSON失败，尝试提取JSON对象")

    # Step 3: 提取JSON对象（字符串感知，兼容截断）
    extracted = _extract_json_object(raw)
    if not extracted:
        raise ValueError("未能从LLM输出中提取到有效的JSON数据，请重试")

    # Step 4: 先做一次轻量规范化（去除非法 + 号）再尝试解析
    normalized = _normalize_json(extracted)
    try:
        return json.loads(normalized)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON解析失败(规范化后): {e}")

        # Step 5: 尝试自动修复（栈式闭合 + 悬空清理）
        fixed = _attempt_fix_json(normalized)
        if fixed:
            try:
                return json.loads(fixed)
            except json.JSONDecodeError as e2:
                logger.warning(f"JSON修复后仍失败: {e2}")

        # 所有尝试都失败，记录预览并返回友好的错误信息
        error_preview = _get_error_preview(text)
        logger.error(f"JSON彻底解析失败，原始预览: {error_preview}")
        raise ValueError(
            f"数据解析异常，请刷新页面重试。"
            f"（错误详情已记录，技术人员正在处理）"
        )


def _remove_markdown_blocks(text: str) -> str:
    """移除markdown代码块标记"""
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json_object(text: str) -> Optional[str]:
    """
    字符串感知地提取最外层 JSON 对象。
    从第一个 '{' 扫描到与之配对的 '}'；若因截断未闭合，则返回从 '{' 到文本末尾，
    交由 _attempt_fix_json 闭合。
    """
    start = text.find('{')
    if start == -1:
        return None

    depth = 0
    in_str = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1].strip()

    # 到末尾仍未闭合（被截断）——返回剩余部分交给修复
    return text[start:].strip()


def _normalize_json(json_str: str) -> str:
    """
    轻量规范化：修复不会改变结构、但违反 JSON 语法的常见问题。
    目前主要修复非法的数字正号前缀：": +1" / "[+1" / ", +1" → 去掉 '+'。
    只匹配紧跟在 : [ , 之后的 +数字，避免误伤字符串内容。
    """
    if not json_str:
        return json_str
    # : +1  |  [ +1  |  , +1   →  去掉 +
    json_str = re.sub(r'([:\[,]\s*)\+(\d)', r'\1\2', json_str)
    return json_str


def _attempt_fix_json(json_str: str) -> Optional[str]:
    """
    尝试修复常见的JSON格式问题（含截断），返回修复后的字符串或None。
    """
    if not json_str:
        return None

    s = _normalize_json(json_str)

    # 1. 去掉末尾多余逗号（如 ",}" ",]"）
    s = re.sub(r',\s*([}\]])', r'\1', s)

    # 2. 栈式闭合被截断的 JSON（未闭合字符串、未配平括号、悬空 key/逗号）
    s = _balance_and_close(s)

    # 3. 再清一次可能出现的 ",}" ",]"
    s = re.sub(r',\s*([}\]])', r'\1', s)

    return s if s else None


def _balance_and_close(s: str) -> str:
    """
    字符串感知地闭合被截断的 JSON：
    - 若结尾停在字符串内部，则补一个引号闭合；
    - 清除结尾的悬空逗号、悬空 key（如 '"reason":'）；
    - 按开括号栈顺序补齐 }/] 。
    """
    stack: List[str] = []
    in_str = False
    escaped = False
    for ch in s:
        if in_str:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch in '{[':
                stack.append(ch)
            elif ch in '}]':
                if stack:
                    stack.pop()

    # 若截断发生在字符串内部，闭合该字符串
    if in_str:
        s = s.rstrip()
        if s.endswith('\\'):          # 去掉悬空的转义符，避免把引号转义掉
            s = s[:-1]
        s += '"'

    # 清理结尾：悬空逗号、悬空 "key": 、再悬空逗号
    s = s.rstrip()
    s = re.sub(r',\s*$', '', s)
    s = re.sub(r'"[^"]*"\s*:\s*$', '', s).rstrip()
    s = re.sub(r',\s*$', '', s)

    # 按栈顺序补齐闭合符
    closer = {'{': '}', '[': ']'}
    s += ''.join(closer[c] for c in reversed(stack))
    return s.strip()


def _smart_close_json(json_str: str) -> str:
    """向后兼容保留：等价于栈式闭合。"""
    return _balance_and_close(_normalize_json(json_str))


def _get_error_preview(text: str, max_length: int = 300) -> str:
    """获取错误预览文本，用于日志记录"""
    preview = text[:max_length]
    if len(text) > max_length:
        preview += "..."
    return preview


def safe_extract_json(text: str, default: Optional[Dict] = None) -> Dict[str, Any]:
    """
    安全的JSON提取函数，不会抛出异常。
    如果提取失败，返回default或空字典。
    """
    try:
        return extract_json_from_text(text)
    except Exception as e:
        logger.error(f"JSON提取失败: {e}", exc_info=True)
        if default is not None:
            return default
        return {}


# 向后兼容的别名
parse_json_from_text = extract_json_from_text