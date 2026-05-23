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
        value = first_json_object(text)
    if not isinstance(value, dict):
        raise ValueError("model output is not a JSON object")
    return value


def first_json_object(text: str) -> object:
    """Return the first syntactically valid JSON value that starts with ``{``."""
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        return value
    raise ValueError("model output does not contain a JSON object")


def coerce_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]
