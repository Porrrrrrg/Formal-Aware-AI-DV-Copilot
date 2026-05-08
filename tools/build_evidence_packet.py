#!/usr/bin/env python3
"""Build a JasperLoop evidence packet from a labeled case JSON and optional reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from tools.parse_jg_report import parse_report
    from tools.parse_jg_trace import parse_trace
    from tools.simple_rtl_context import extract_context
    from tools.summarize_counterexample import summarize
except ModuleNotFoundError:
    from parse_jg_report import parse_report
    from parse_jg_trace import parse_trace
    from simple_rtl_context import extract_context
    from summarize_counterexample import summarize

ALLOWED_ISSUE_TYPES = [
    "rtl_design_bug",
    "assertion_property_bug",
    "assumption_constraint_bug",
    "testbench_stimulus_bug",
    "reachable_coverage_gap",
    "unreachable_or_invalid_coverage_goal",
]

ALLOWED_NEXT_ACTIONS = [
    "fix_rtl",
    "fix_assertion_property",
    "fix_assumption_constraint",
    "fix_testbench_or_stimulus",
    "add_directed_test_or_sequence",
    "prove_unreachable_or_waive_coverage_goal",
    "rerun_jaspergold",
]


def load_json(path: Path | None) -> object:
    if not path or not path.exists():
        return None
    return json.loads(path.read_text())


def build_packet(
    case_path: Path,
    report_path: Path | None = None,
    trace_path: Path | None = None,
    rtl_paths: list[Path] | None = None,
) -> dict[str, object]:
    case = json.loads(case_path.read_text())
    property_results = parse_report(report_path) if report_path and report_path.exists() else []
    trace = parse_trace(trace_path) if trace_path and trace_path.exists() else {}
    cex_summary = summarize(trace, case.get("property_id")) if trace else {}
    rtl_context = extract_context(rtl_paths or []) if rtl_paths else {}

    return {
        "case_id": case["case_id"],
        "design_id": case["design_id"],
        "variant": case.get("variant"),
        "task_type": case.get("task_type", "failure_triage"),
        "design_intent": case.get("design_intent", []),
        "failing_property": {
            "property_id": case.get("property_id"),
            "intent": case.get("property_intent"),
            "expected_issue_type": case.get("expected_issue_type"),
        },
        "active_assumptions": case.get("active_assumptions", []),
        "jasper_result": {
            "properties": property_results,
            "source_report": str(report_path) if report_path else None,
        },
        "counterexample_summary": cex_summary,
        "coverage_context": case.get("coverage_context", {}),
        "rtl_context": rtl_context,
        "assertion_intent": case.get("assertion_intent", {}),
        "assumption_risks": case.get("assumption_risks", []),
        "allowed_issue_types": ALLOWED_ISSUE_TYPES,
        "allowed_next_actions": ALLOWED_NEXT_ACTIONS,
        "gold_label": {
            "issue_type": case.get("expected_issue_type"),
            "next_action": case.get("expected_next_action"),
            "root_cause": case.get("root_cause"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--trace", type=Path)
    parser.add_argument("--rtl", nargs="*", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    packet = build_packet(args.case, args.report, args.trace, args.rtl)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(packet, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
