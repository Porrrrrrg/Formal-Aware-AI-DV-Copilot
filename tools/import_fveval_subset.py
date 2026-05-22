#!/usr/bin/env python3
"""Offline importer for FVEval-like local fixture folders.

This importer intentionally reads only local files. It supports flat folders and
the common subset-style layout:

- NL2SVA-Human/
- NL2SVA-Machine/
- Design2SVA/

Rows may be JSON objects, JSON arrays, JSONL records, or CSV rows. The output is
a normalized fixture JSON file that can feed later JasperLoop Design2SVA/NL2SVA
experiments without downloading or bundling the full FVEval dataset.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

SUBSET_DIR_NAMES = {
    "nl2sva-human": "NL2SVA-Human",
    "nl2sva_human": "NL2SVA-Human",
    "nl2sva-machine": "NL2SVA-Machine",
    "nl2sva_machine": "NL2SVA-Machine",
    "design2sva": "Design2SVA",
}


def load_fixture_rows(source_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in iter_data_files(source_dir):
        subset = infer_subset(path, source_dir)
        for row in load_file_rows(path):
            row = dict(row)
            row.setdefault("subset", subset)
            row.setdefault("path", str(path.relative_to(source_dir)))
            rows.append(row)
    return rows


def iter_data_files(source_dir: Path) -> list[Path]:
    suffixes = {".json", ".jsonl", ".csv"}
    return sorted(path for path in source_dir.rglob("*") if path.is_file() and path.suffix.lower() in suffixes)


def infer_subset(path: Path, source_dir: Path) -> str:
    try:
        parts = path.relative_to(source_dir).parts
    except ValueError:
        parts = path.parts
    for part in parts[:-1]:
        normalized = part.lower()
        if normalized in SUBSET_DIR_NAMES:
            return SUBSET_DIR_NAMES[normalized]
    return "Local-FVEval-Fixture"


def load_file_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        records = data.get("records") or data.get("cases") or data.get("tasks")
        if isinstance(records, list):
            return [item for item in records if isinstance(item, dict)]
        return [data]
    return []


def normalize_case(row: dict[str, Any], index: int, source_dir: Path) -> dict[str, Any]:
    subset = str(row.get("subset") or "Local-FVEval-Fixture")
    case_id = str(row.get("case_id") or row.get("task_id") or f"local_fveval_{index:04d}")
    property_id = str(row.get("property_id") or f"{case_id}_property")
    intent = str(
        row.get("intent")
        or row.get("property_intent")
        or row.get("instruction")
        or row.get("prompt")
        or row.get("nl")
        or ""
    )
    allowed_signals = normalize_signal_list(row.get("allowed_signals") or row.get("signals") or [])
    return {
        "case_id": case_id,
        "source_task_id": str(row.get("source_task_id") or row.get("id") or case_id),
        "subset": subset,
        "task_family": task_family_for_subset(subset),
        "design_id": str(row.get("design_id") or row.get("design") or "unknown_design"),
        "property_id": property_id,
        "clock": str(row.get("clock") or "clk"),
        "reset": str(row.get("reset") or ""),
        "problem_spec": str(row.get("problem_spec") or row.get("rtl") or row.get("design_text") or intent),
        "property_intent": intent or "Generate one useful concurrent SystemVerilog assertion.",
        "allowed_signals": allowed_signals,
        "signals": allowed_signals,
        "expected_sva": row.get("expected_sva"),
        "reference_sva": row.get("reference_sva") or row.get("assertion"),
        "testbench_header": row.get("testbench_header") or row.get("harness_header"),
        "testbench": row.get("testbench") or row.get("harness"),
        "source": {
            "repository": str(row.get("repository") or "local_fixture"),
            "path": str(row.get("path") or source_dir),
            "commit": str(row.get("commit") or "local"),
            "license": str(row.get("license") or "unknown"),
        },
        "notes": "Reference SVA is evaluation-only and must not be included in model prompts.",
    }


def task_family_for_subset(subset: str) -> str:
    if subset == "Design2SVA":
        return "design2sva"
    if subset in {"NL2SVA-Human", "NL2SVA-Machine"}:
        return "nl2sva"
    return "unknown"


def normalize_signal_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str):
        return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument(
        "--out",
        default=Path("benchmarks/external/fveval_subset/local_import_cases.json"),
        type=Path,
    )
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    rows = load_fixture_rows(args.source_dir)
    if args.limit is not None:
        rows = rows[: args.limit]
    cases = [normalize_case(row, index, args.source_dir) for index, row in enumerate(rows)]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(cases, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_dir": str(args.source_dir), "cases": len(cases), "out": str(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
