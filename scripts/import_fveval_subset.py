#!/usr/bin/env python3
"""Scaffold importer for local FVEval-like fixture folders.

The importer is intentionally offline-only. It reads a user-supplied local
folder containing JSON or CSV rows and writes a sanitized JasperLoop-compatible
case file. It does not download NVlabs/FVEval or any private/commercial data.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def load_rows(source_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(source_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            rows.extend(item for item in data if isinstance(item, dict))
        elif isinstance(data, dict):
            rows.append(data)
    for path in sorted(source_dir.glob("*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            rows.extend(dict(row) for row in csv.DictReader(handle))
    return rows


def normalize_case(row: dict[str, Any], index: int, source_dir: Path) -> dict[str, Any]:
    case_id = str(row.get("case_id") or row.get("task_id") or f"local_fveval_{index:04d}")
    property_id = str(row.get("property_id") or f"{case_id}_property")
    intent = str(row.get("property_intent") or row.get("instruction") or row.get("prompt") or "")
    rtl = str(row.get("rtl") or row.get("problem_spec") or row.get("design") or "")
    signals = row.get("signals") or row.get("allowed_signals") or []
    if isinstance(signals, str):
        signals = [item.strip() for item in signals.replace(";", ",").split(",") if item.strip()]
    return {
        "case_id": case_id,
        "source_task_id": str(row.get("source_task_id") or case_id),
        "subset": str(row.get("subset") or "Local-FVEval-Fixture"),
        "design_id": str(row.get("design_id") or row.get("design") or "unknown_design"),
        "property_id": property_id,
        "clock": str(row.get("clock") or "clk"),
        "reset": str(row.get("reset") or ""),
        "problem_spec": rtl or intent,
        "property_intent": intent or "Generate one useful concurrent SystemVerilog assertion.",
        "allowed_signals": list(signals),
        "signals": list(signals),
        "expected_sva": row.get("expected_sva"),
        "reference_sva": row.get("reference_sva"),
        "testbench_header": row.get("testbench_header"),
        "testbench": row.get("testbench"),
        "source": {
            "repository": str(row.get("repository") or "local_fixture"),
            "path": str(row.get("path") or source_dir),
            "commit": str(row.get("commit") or "local"),
            "license": str(row.get("license") or "unknown"),
        },
        "notes": "Reference SVA is evaluation-only and must not be included in model prompts.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--out", default=Path("benchmarks/fveval_subset/local_import_cases.json"), type=Path)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    rows = load_rows(args.source_dir)
    if args.limit is not None:
        rows = rows[: args.limit]
    cases = [normalize_case(row, index, args.source_dir) for index, row in enumerate(rows)]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(cases, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_dir": str(args.source_dir), "cases": len(cases), "out": str(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
