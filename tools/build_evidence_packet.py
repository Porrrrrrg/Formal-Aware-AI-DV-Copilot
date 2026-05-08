#!/usr/bin/env python3
"""Build a JasperLoop evidence packet from a labeled case JSON and optional reports."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from tools.manifest_utils import infer_signal_role_map_path, load_signal_role_map
    from tools.parse_jg_report import parse_report, summarize_properties
    from tools.parse_jg_trace import parse_trace
    from tools.simple_rtl_context import extract_context
    from tools.summarize_counterexample import summarize
except ModuleNotFoundError:
    from manifest_utils import infer_signal_role_map_path, load_signal_role_map
    from parse_jg_report import parse_report, summarize_properties
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
    trace_dir: Path | None = None,
    rtl_paths: list[Path] | None = None,
    signal_role_map_path: Path | None = None,
    include_gold: bool = False,
) -> dict[str, object]:
    case = json.loads(case_path.read_text())
    if signal_role_map_path is None:
        signal_role_map_path = infer_signal_role_map_path(case_path)
    signal_roles = load_signal_role_map(signal_role_map_path)
    property_results = parse_report(report_path) if report_path and report_path.exists() else []
    result_summary = summarize_properties(property_results)

    trace_paths: list[Path] = []
    if trace_path and trace_path.exists():
        trace_paths.append(trace_path)
    if trace_dir and trace_dir.exists():
        trace_paths.extend(sorted(trace_dir.glob("*.vcd")))
        trace_paths.extend(sorted(trace_dir.glob("*.vcd.gz")))

    trace_paths = sort_trace_paths(
        trace_paths,
        result_summary.get("falsified_properties", []),
        case.get("property_id"),
    )

    parsed_traces = [parse_trace(path) for path in trace_paths]
    trace_summaries = [
        {
            "trace_file": trace.get("trace_file"),
            "trace_format": trace.get("trace_format"),
            "property_id": trace.get("property_id"),
            "summary": summarize(trace, case.get("property_id"), signal_roles),
        }
        for trace in parsed_traces
    ]
    cex_summary = trace_summaries[0]["summary"] if trace_summaries else {}
    if isinstance(cex_summary, dict):
        cex_summary["falsified_properties"] = result_summary.get("falsified_properties", [])

    rtl_context = extract_context(rtl_paths or []) if rtl_paths else {}

    packet = {
        "case_id": case["case_id"],
        "design_id": case["design_id"],
        "variant": case.get("variant"),
        "task_type": case.get("task_type", "failure_triage"),
        "design_intent": case.get("design_intent", []),
        "failing_property": {
            "property_id": case.get("property_id"),
            "intent": case.get("property_intent"),
        },
        "active_assumptions": case.get("active_assumptions", []),
        "jasper_result": {
            "summary": result_summary,
            "properties": property_results,
            "source_report": str(report_path) if report_path else None,
            "trace_files": [str(path) for path in trace_paths],
        },
        "counterexample_summary": cex_summary,
        "trace_summaries": trace_summaries,
        "signal_role_map": signal_roles,
        "coverage_context": case.get("coverage_context", {}),
        "rtl_context": rtl_context,
        "assertion_intent": case.get("assertion_intent", {}),
        "assumption_risks": case.get("assumption_risks", []),
        "allowed_issue_types": ALLOWED_ISSUE_TYPES,
        "allowed_next_actions": ALLOWED_NEXT_ACTIONS,
    }

    if include_gold:
        packet["gold_label"] = {
            "issue_type": case.get("expected_issue_type"),
            "next_action": case.get("expected_next_action"),
            "root_cause": case.get("root_cause"),
        }

    return packet


def sort_trace_paths(
    paths: list[Path],
    falsified_properties: object,
    focus_property: object = None,
) -> list[Path]:
    falsified = set(falsified_properties if isinstance(falsified_properties, list) else [])
    focus = str(focus_property) if focus_property else None

    def key(path: Path) -> tuple[int, str]:
        property_id = infer_property_from_name(path.name)
        is_focus = property_id == focus
        is_falsified = property_id in falsified
        return (0 if is_focus else 1, 0 if is_falsified else 1, path.name)

    unique = {str(path): path for path in paths}
    return sorted(unique.values(), key=key)


def infer_property_from_name(name: str) -> str | None:
    match = re.search(r"\.(?:properties_i|assumptions_i)\.([A-Za-z0-9_:]+)\.", name)
    if match:
        return match.group(1)
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--trace", type=Path)
    parser.add_argument("--trace-dir", type=Path)
    parser.add_argument("--rtl", nargs="*", type=Path)
    parser.add_argument("--signal-role-map", type=Path)
    parser.add_argument("--include-gold", action="store_true")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    packet = build_packet(
        args.case,
        args.report,
        args.trace,
        args.trace_dir,
        args.rtl,
        args.signal_role_map,
        args.include_gold,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(packet, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
