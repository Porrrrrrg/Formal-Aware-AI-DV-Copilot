#!/usr/bin/env python3
"""Scaffold evaluation runner for labeled JSON cases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from metrics import accuracy


def iter_cases(paths: list[Path]) -> list[dict[str, object]]:
    cases = []
    for path in paths:
        if path.is_dir():
            files = sorted(path.glob("*.json"))
        else:
            files = [path]
        for file in files:
            data = json.loads(file.read_text())
            data["_file"] = str(file)
            cases.append(data)
    return cases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", nargs="+", required=True, type=Path)
    args = parser.parse_args()

    cases = iter_cases(args.cases)
    rows = []
    for case in cases:
        rows.append(
            {
                "case_id": case.get("case_id"),
                "predicted_issue_type": case.get("expected_issue_type"),
                "gold_issue_type": case.get("expected_issue_type"),
                "predicted_next_action": case.get("expected_next_action"),
                "gold_next_action": case.get("expected_next_action"),
            }
        )

    summary = {
        "num_cases": len(rows),
        "issue_type_accuracy_oracle_scaffold": accuracy(
            rows, "predicted_issue_type", "gold_issue_type"
        ),
        "next_action_accuracy_oracle_scaffold": accuracy(
            rows, "predicted_next_action", "gold_next_action"
        ),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
