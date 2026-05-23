#!/usr/bin/env python3
"""Write the curated Codex/LLM subset gate summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evaluation" / "results"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate-failed", action="store_true")
    parser.add_argument("--reason", default="")
    args = parser.parse_args()

    payloads = load_payloads()
    lines = [
        "# Codex/LLM Subset Quality Gate",
        "",
        "This file is a curated gate summary. It separates real LLM success from deterministic fallback behavior.",
        "",
    ]
    if args.gate_failed:
        lines.extend(
            [
                "Gate result: **failed; benchmark subset was not rerun**.",
                "",
                f"Reason: {args.reason or 'backend doctor or contract test failed.'}",
                "",
            ]
        )
    else:
        lines.extend(["Gate result: see task rows below.", ""])

    lines.extend(
        [
            "| Task | Cases | LLM Success | Fallback Rate | LLM Error Rate | Hallucinated Signal Rate | Accuracy Metric |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in summarize_payloads(payloads):
        lines.append(
            "| {task} | {cases} | {llm_success:.3f} | {fallback:.3f} | {llm_error:.3f} | "
            "{hallucination} | {accuracy} |".format(**row)
        )

    lines.extend(
        [
            "",
            "Gate policy:",
            "",
            "- JSON validity below 0.90: stop full run.",
            "- Fallback rate above 0.25: stop full run.",
            "- Fallback-only results are failed environment gates, not model performance.",
            "",
            "Real LLM performance requires outputs with `source`/`output_source` equivalent to `llm` and no fallback error.",
        ]
    )
    (RESULTS / "codex_subset_quality.md").write_text("\n".join(lines) + "\n")
    return 0


def load_payloads() -> dict[str, dict[str, Any]]:
    files = {
        "sva_repair": RESULTS / "sva_repair_codex_subset.json",
        "triage": RESULTS / "agent_eval_codex_subset.json",
        "coverage": RESULTS / "coverage_eval_codex_subset.json",
    }
    payloads: dict[str, dict[str, Any]] = {}
    for task, path in files.items():
        if path.exists():
            payloads[task] = json.loads(path.read_text())
    return payloads


def summarize_payloads(payloads: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    if "sva_repair" in payloads:
        summary = payloads["sva_repair"].get("summary", {})
        rows.append(
            make_row(
                "SVA repair",
                summary,
                hallucination=summary.get("hallucinated_signal_rate", 0.0),
                accuracy=f"final exact match {float(summary.get('exact_match_final', 0.0)):.3f}",
            )
        )
    if "triage" in payloads:
        summary = payloads["triage"].get("systems", {}).get("structured", {})
        rows.append(
            make_row(
                "Failure triage",
                summary,
                hallucination=summary.get("hallucinated_signal_rate", 0.0),
                accuracy=(
                    f"issue/action {float(summary.get('issue_type_accuracy', 0.0)):.3f}/"
                    f"{float(summary.get('next_action_accuracy', 0.0)):.3f}"
                ),
            )
        )
    if "coverage" in payloads:
        summary = payloads["coverage"].get("systems", {}).get("structured", {})
        rows.append(
            make_row(
                "Coverage closure",
                summary,
                hallucination="n/a",
                accuracy=(
                    f"gap/action {float(summary.get('gap_type_accuracy', 0.0)):.3f}/"
                    f"{float(summary.get('action_accuracy', 0.0)):.3f}"
                ),
            )
        )
    if not rows:
        rows.append(
            {
                "task": "No subset outputs",
                "cases": 0,
                "llm_success": 0.0,
                "fallback": 0.0,
                "llm_error": 0.0,
                "hallucination": "n/a",
                "accuracy": "n/a",
            }
        )
    return rows


def make_row(
    task: str,
    summary: dict[str, Any],
    hallucination: object,
    accuracy: str,
) -> dict[str, Any]:
    hallucination_text = (
        f"{float(hallucination):.3f}" if isinstance(hallucination, (int, float)) else str(hallucination)
    )
    return {
        "task": task,
        "cases": int(summary.get("num_cases", 0) or 0),
        "llm_success": float(summary.get("llm_success_rate", 0.0) or 0.0),
        "fallback": float(summary.get("fallback_rate", 0.0) or 0.0),
        "llm_error": float(summary.get("llm_error_rate", 0.0) or 0.0),
        "hallucination": hallucination_text,
        "accuracy": accuracy,
    }


if __name__ == "__main__":
    raise SystemExit(main())
