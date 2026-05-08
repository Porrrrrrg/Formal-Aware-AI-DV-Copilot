#!/usr/bin/env python3
"""Replay previously generated JSON LLM outputs for offline evaluation.

The adapter reads a prompt from stdin, extracts stable identifiers such as
case_id and ROUND, and writes the matching JSON response from a local JSON or
JSONL file. It is meant for importing Codex/LLM outputs generated outside this
workspace without sending prompts externally from the evaluation runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


CASE_ID_RE = re.compile(r'"case_id"\s*:\s*"([^"]+)"')
PROPERTY_ID_RE = re.compile(r'"property_id"\s*:\s*"([^"]+)"')
ROUND_RE = re.compile(r"\bROUND:\s*(\d+)\b")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument(
        "--strict-round",
        action="store_true",
        help="Require the response round to match ROUND in the prompt.",
    )
    args = parser.parse_args()

    prompt = sys.stdin.read()
    records = load_records(args.responses)
    key = prompt_key(prompt)
    response = select_response(records, key, strict_round=args.strict_round)
    if response is None:
        sys.stderr.write(
            "No replay response found for "
            f"case_id={key.case_id!r}, property_id={key.property_id!r}, "
            f"round={key.round_index!r}, prompt_sha256={key.prompt_sha256}.\n"
        )
        return 3
    sys.stdout.write(json.dumps(response, indent=2) + "\n")
    return 0


class PromptKey:
    def __init__(
        self,
        case_id: str | None,
        property_id: str | None,
        round_index: int | None,
        prompt_sha256: str,
    ) -> None:
        self.case_id = case_id
        self.property_id = property_id
        self.round_index = round_index
        self.prompt_sha256 = prompt_sha256


def prompt_key(prompt: str) -> PromptKey:
    case_id = first_match(CASE_ID_RE, prompt)
    property_id = first_match(PROPERTY_ID_RE, prompt)
    round_text = first_match(ROUND_RE, prompt)
    round_index = int(round_text) if round_text else None
    prompt_sha256 = hashlib.sha256(prompt.encode()).hexdigest()
    return PromptKey(case_id, property_id, round_index, prompt_sha256)


def first_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(1) if match else None


def load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text().strip()
    if not text:
        return []
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text)
    if isinstance(data, list):
        return [record for record in data if isinstance(record, dict)]
    if isinstance(data, dict) and isinstance(data.get("responses"), list):
        return [record for record in data["responses"] if isinstance(record, dict)]
    if isinstance(data, dict):
        return [data]
    raise ValueError(f"Unsupported replay response format: {path}")


def select_response(
    records: list[dict[str, Any]],
    key: PromptKey,
    strict_round: bool = False,
) -> dict[str, Any] | None:
    scored: list[tuple[int, dict[str, Any]]] = []
    for record in records:
        response = normalize_record_response(record)
        if response is None:
            continue
        score = record_score(record, key, strict_round=strict_round)
        if score > 0:
            scored.append((score, response))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def normalize_record_response(record: dict[str, Any]) -> dict[str, Any] | None:
    response = record.get("response")
    if isinstance(response, dict):
        return response
    if isinstance(record.get("output"), dict):
        return record["output"]
    reserved = {
        "task",
        "case_id",
        "property_id",
        "prompt_id",
        "prompt_sha256",
        "round",
        "round_index",
    }
    candidate = {key: value for key, value in record.items() if key not in reserved}
    return candidate or None


def record_score(record: dict[str, Any], key: PromptKey, strict_round: bool = False) -> int:
    score = 0
    record_round = int(record.get("round", record.get("round_index", 0)) or 0)
    if strict_round and key.round_index is not None and record_round not in {0, key.round_index}:
        return 0
    if key.prompt_sha256 and record.get("prompt_sha256") == key.prompt_sha256:
        score += 100
    if key.case_id and record.get("case_id") == key.case_id:
        score += 50
    if key.property_id and record.get("property_id") == key.property_id:
        score += 20
    if key.round_index is not None and record_round == key.round_index:
        score += 10
    return score


if __name__ == "__main__":
    raise SystemExit(main())
