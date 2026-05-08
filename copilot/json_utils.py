"""JSON helpers for agent outputs."""

from __future__ import annotations

import json


def extract_json_object(text: str) -> dict[str, object]:
    """Extract a JSON object from raw model output."""
    text = text.strip()
    if not text:
        raise ValueError("empty model output")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < start:
            raise
        value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("model output is not a JSON object")
    return value


def coerce_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]
