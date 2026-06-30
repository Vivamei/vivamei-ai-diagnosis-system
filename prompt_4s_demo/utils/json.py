"""
utils/json.py

JSON extraction utilities.
"""

import json
import re


def extract_json_from_text(text: str) -> dict:
    """Extract JSON from LLM response text, handling markdown code blocks."""
    raw = text.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError("LLM output is not valid JSON.")
