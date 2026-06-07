#!/usr/bin/env python3
"""Write a local LLM subset gate summary.

The subset gate is an operational diagnostic, not a final curated result. Its
summary is written under ignored artifacts by default so the final repository
keeps only evaluation/results/final_results.md as the committed result table.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evaluation" / "results"
DEFAULT_OUT = ROOT / "artifacts" / "llm_subset_gate" / "quality.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate-failed", action="store_true")
    parser.add_argument("--reason", default="")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    payloads = load_payloads()
    gate = gate_status(payloads)
    lines = [
        "# LLM Subset Quality Gate",
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
        lines.extend([f"Gate result: {gate['summary']}", ""])
        if os.environ.get("JASPERLOOP_LLM_CMD"):
            model = os.environ.get("SERVED_MODEL_NAME")
            base_url = os.environ.get("LOCAL_BASE_URL")
            lines.extend(
                [
                    "Backend route: generic `JASPERLOOP_LLM_CMD` real local/backend LLM route.",
                    f"Model endpoint: {model or 'configured by backend command'}"
                    + (f" at `{base_url}`." if base_url else "."),
                    "Result type: real local/backend LLM subset gate, not Codex CLI performance and not JasperGold-backed performance.",
                    "",
                ]
            )

    lines.extend(
        [
            "| Task | Cases | Valid JSON | LLM Success | Fallback Rate | LLM Error Rate | Hallucinated Signal Rate | Accuracy Metric |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in summarize_payloads(payloads):
        lines.append(
            "| {task} | {cases} | {valid_json:.3f} | {llm_success:.3f} | {fallback:.3f} | {llm_error:.3f} | "
            "{hallucination} | {accuracy} |".format(**row)
        )

    if not args.gate_failed and gate["failures"]:
        lines.extend(["", "Gate blockers:", ""])
        lines.extend(f"- {failure}" for failure in gate["failures"])

    lines.extend(
        [
            "",
            "Gate policy:",
            "",
            "- JSON validity below 0.90: stop full run.",
            "- Fallback rate above 0.25: stop full run.",
            "- Hallucinated signal rate above 0.10: stop full run.",
            "- Fallback-only results are failed environment gates, not model performance.",
            "",
            "Real LLM performance requires outputs with `source`/`output_source` equivalent to `llm` and no fallback error.",
        ]
    )
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n")
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
        "valid_json": float(summary.get("valid_json_rate", 0.0) or 0.0),
        "llm_success": float(summary.get("llm_success_rate", 0.0) or 0.0),
        "fallback": float(summary.get("fallback_rate", 0.0) or 0.0),
        "llm_error": float(summary.get("llm_error_rate", 0.0) or 0.0),
        "hallucination": hallucination_text,
        "accuracy": accuracy,
    }


def gate_status(payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    failures: list[str] = []
    for row in summarize_payloads(payloads):
        task = str(row["task"])
        if task == "No subset outputs":
            failures.append("No subset output files were available.")
            continue
        if float(row["valid_json"]) < 0.90:
            failures.append(f"{task}: JSON validity {float(row['valid_json']):.3f} is below 0.90.")
        if float(row["fallback"]) > 0.25:
            failures.append(f"{task}: fallback rate {float(row['fallback']):.3f} is above 0.25.")
        hallucination = row["hallucination"]
        if isinstance(hallucination, str) and hallucination == "n/a":
            continue
        if float(hallucination) > 0.10:
            failures.append(f"{task}: hallucinated signal rate {float(hallucination):.3f} is above 0.10.")
    if failures:
        return {"passed": False, "failures": failures, "summary": "failed; full benchmark remains blocked."}
    return {"passed": True, "failures": [], "summary": "passed; full benchmark is allowed next but was not run."}


if __name__ == "__main__":
    raise SystemExit(main())
