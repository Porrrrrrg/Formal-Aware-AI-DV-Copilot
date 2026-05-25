#!/usr/bin/env python3
"""Build a JasperLoop evidence packet from a labeled case JSON and optional reports."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from tools.coverage_utils import build_coverage_evidence, enrich_coverage_context
    from tools.manifest_utils import infer_signal_role_map_path, load_signal_role_map
    from tools.parse_jg_report import parse_report_payload, summarize_properties
    from tools.parse_jg_trace import parse_trace
    from tools.simple_rtl_context import extract_context
    from tools.summarize_counterexample import summarize
except ModuleNotFoundError:
    from coverage_utils import build_coverage_evidence, enrich_coverage_context
    from manifest_utils import infer_signal_role_map_path, load_signal_role_map
    from parse_jg_report import parse_report_payload, summarize_properties
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

OVERCONSTRAINT_WORDS = (
    "force",
    "forces",
    "forbid",
    "forbids",
    "restrict",
    "restricts",
    "keep",
    "keeps",
    "hold",
    "holds",
    "stuck",
    "never",
)

UNDERCONSTRAINT_WORDS = (
    "contract should constrain",
    "should constrain",
    "missing assumption",
    "missing constraint",
    "environment may",
    "producer-side contract",
)

STIMULUS_WORDS = (
    "simulation should",
    "stimulus should",
    "testbench stimulus",
    "should exercise",
)


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
    report_payload = (
        parse_report_payload(report_path)
        if report_path and report_path.exists()
        else {"summary": summarize_properties([]), "properties": [], "parser_errors": []}
    )
    property_results = list(report_payload.get("properties", []))
    result_summary = dict(report_payload.get("summary", summarize_properties(property_results)))

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
            "witness_events": render_witness_events(trace),
            "parser_errors": trace.get("parser_errors", []),
        }
        for trace in parsed_traces
    ]
    cex_summary = trace_summaries[0]["summary"] if trace_summaries else {}
    if isinstance(cex_summary, dict):
        cex_summary["falsified_properties"] = result_summary.get("falsified_properties", [])

    rtl_context = extract_context(rtl_paths or []) if rtl_paths else {}
    coverage_context = enrich_coverage_context(case_path, case)

    coverage_evidence = build_coverage_evidence(
        coverage_context,
        trace_summaries,
        property_results,
        result_summary,
    )

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
            "parser_errors": report_payload.get("parser_errors", []),
            "focus_property_result": focus_property_result(property_results, case.get("property_id")),
            "source_report": str(report_path) if report_path else None,
            "trace_files": [str(path) for path in trace_paths],
        },
        "counterexample_summary": cex_summary,
        "trace_summaries": trace_summaries,
        "signal_role_map": signal_roles,
        "coverage_context": coverage_context,
        "coverage_evidence": coverage_evidence,
        "witness_events": coverage_evidence.get("witness_events", [])
        if isinstance(coverage_evidence, dict)
        else [],
        "stimulus_context": build_stimulus_context(case, coverage_context, coverage_evidence),
        "vacuity_context": build_vacuity_context(case, property_results, result_summary),
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


def render_witness_events(trace: dict[str, object], limit: int = 8) -> list[str]:
    events = trace.get("events")
    if not isinstance(events, list):
        return []
    rendered: list[str] = []
    for event in events[:limit]:
        if not isinstance(event, dict):
            continue
        cycle = event.get("cycle")
        changes = event.get("changes") or {
            signal: value
            for signal, value in (event.get("signals") or {}).items()
            if isinstance(event.get("signals"), dict)
        }
        if isinstance(changes, dict) and changes:
            body = ", ".join(f"{key}={value}" for key, value in list(changes.items())[:6])
            rendered.append(f"cycle {cycle}: {body}")
    return rendered


def focus_property_result(
    property_results: list[dict[str, object]],
    property_id: object,
) -> dict[str, object]:
    focus = str(property_id or "")
    if not focus:
        return {}
    for result in property_results:
        name = str(result.get("property_id", ""))
        if name == focus or name.endswith("." + focus) or focus in name:
            return result
    return {}


def build_vacuity_context(
    case: dict[str, object],
    property_results: list[dict[str, object]],
    result_summary: dict[str, object],
) -> dict[str, object]:
    vacuous_properties = result_summary.get("vacuous_properties", [])
    if not vacuous_properties:
        vacuous_properties = [
            result.get("property_id")
            for result in property_results
            if str(result.get("status", "")).lower() == "vacuous"
        ]
    active_assumptions = case.get("active_assumptions", [])
    suspect_assumptions = [
        item.get("id")
        for item in active_assumptions
        if isinstance(item, dict) and item.get("id")
    ]
    assumption_risk_cues = assumption_vacuity_risk_cues(case, vacuous_properties)
    has_overconstraint = any(
        cue["kind"] in {"blocking_assumption", "reset_stuck_assumption"}
        for cue in assumption_risk_cues
    )
    has_underconstraint = any(cue["kind"] == "missing_environment_constraint" for cue in assumption_risk_cues)
    if has_overconstraint:
        constraint_direction = "overconstraint"
    elif has_underconstraint:
        constraint_direction = "underconstraint"
    else:
        constraint_direction = "unknown"
    reason = ""
    if vacuous_properties and suspect_assumptions:
        reason = "Active assumptions may make the target antecedent or coverage goal unreachable."
    elif has_overconstraint:
        reason = (
            "Active assumptions contain blocking/reset-stuck cues; review whether "
            "they remove legal trigger behavior before blaming the assertion."
        )
    elif has_underconstraint:
        reason = "The property intent describes an environment contract or missing constraint; review underconstraint before blaming the assertion."
    return {
        "vacuity_status": "vacuous" if vacuous_properties else "not_observed",
        "vacuous_properties": [str(item) for item in vacuous_properties if item],
        "suspect_assumptions": [str(item) for item in suspect_assumptions],
        "assumption_risk_cues": assumption_risk_cues,
        "constraint_direction": constraint_direction,
        "requires_assumption_review": bool(assumption_risk_cues or vacuous_properties),
        "reason": reason,
    }


def assumption_vacuity_risk_cues(
    case: dict[str, object],
    vacuous_properties: object,
) -> list[dict[str, str]]:
    cues: list[dict[str, str]] = []
    active_assumptions = case.get("active_assumptions", [])
    if isinstance(active_assumptions, list):
        for item in active_assumptions:
            if not isinstance(item, dict):
                continue
            assumption_id = str(item.get("id", ""))
            intent = str(item.get("intent", ""))
            lowered = intent.lower()
            matched_words = [word for word in OVERCONSTRAINT_WORDS if word in lowered]
            if not matched_words:
                continue
            reset_stuck = "reset" in lowered and any(
                word in lowered for word in ("stuck", "hold", "holds", "keep", "keeps")
            )
            kind = "reset_stuck_assumption" if reset_stuck else "blocking_assumption"
            cues.append(
                {
                    "kind": kind,
                    "assumption_id": assumption_id,
                    "intent": intent,
                    "cue": ", ".join(sorted(set(matched_words))),
                    "interpretation": (
                        "This assumption may block legal behavior needed by the "
                        "failing property or coverage goal."
                    ),
                }
            )

    property_text = " ".join(
        str(case.get(key, ""))
        for key in ("property_id", "property_intent")
    ).lower()
    matched_underconstraint = [word for word in UNDERCONSTRAINT_WORDS if word in property_text]
    if matched_underconstraint:
        cues.append(
            {
                "kind": "missing_environment_constraint",
                "assumption_id": "",
                "intent": str(case.get("property_intent", "")),
                "cue": ", ".join(sorted(set(matched_underconstraint))),
                "interpretation": "The failure may be caused by an underconstrained environment contract rather than a bad assertion.",
            }
        )

    if vacuous_properties:
        cues.append(
            {
                "kind": "vacuous_property",
                "assumption_id": "",
                "intent": ", ".join(str(item) for item in vacuous_properties if item),
                "cue": "vacuous_property",
                "interpretation": "A vacuous result requires assumption and trigger-reachability review before an assertion fix.",
            }
        )
    return cues


def build_stimulus_context(
    case: dict[str, object],
    coverage_context: dict[str, object],
    coverage_evidence: dict[str, object],
) -> dict[str, object]:
    coverage = coverage_context if isinstance(coverage_context, dict) else {}
    evidence = coverage_evidence if isinstance(coverage_evidence, dict) else {}
    task_type = str(case.get("task_type", ""))
    property_id = str(case.get("property_id", ""))
    property_intent = str(case.get("property_intent", ""))
    design_intent = case.get("design_intent", [])
    design_text = " ".join(str(item) for item in design_intent) if isinstance(design_intent, list) else str(design_intent)
    combined_text = " ".join([property_id, property_intent, design_text]).lower()
    expected_reachable = coverage.get("expected_reachable")
    expected_hits = coverage.get("expected_test_hits")
    cover_status = str(
        evidence.get("observed_cover_status") or coverage.get("expected_cover_status") or ""
    ).lower()
    suggested_sequence = coverage.get("suggested_sequence")
    has_suggested_sequence = isinstance(suggested_sequence, list) and bool(suggested_sequence)
    witness_events = evidence.get("witness_events")
    has_witness = isinstance(witness_events, list) and bool(witness_events)
    related_signals = coverage.get("related_signals")
    related_signal_text = " ".join(str(signal) for signal in related_signals) if isinstance(related_signals, list) else ""

    cues: list[dict[str, str]] = []
    is_invalid = expected_reachable is False or cover_status == "unreachable"
    if is_invalid:
        cues.append(
            {
                "kind": "invalid_or_unreachable_cover_goal",
                "cue": "expected_reachable_false_or_unreachable_status",
                "interpretation": "The coverage goal is illegal, unreachable, or invalid under the available design and coverage evidence.",
            }
        )
    else:
        stimulus_terms = [word for word in STIMULUS_WORDS if word in combined_text]
        if task_type == "failure_triage" and stimulus_terms:
            cues.append(
                {
                    "kind": "missing_required_stimulus",
                    "cue": ", ".join(sorted(set(stimulus_terms))),
                    "interpretation": "The evidence frames the failure as missing or insufficient simulation/testbench stimulus.",
                }
            )
        if (
            task_type == "failure_triage"
            and coverage
            and expected_reachable is True
            and expected_hits in {0, "0", None}
            and not has_suggested_sequence
            and not has_witness
        ):
            cues.append(
                {
                    "kind": "cover_goal_unhit_because_stimulus_absent",
                    "cue": "failure_triage_unhit_reachable_cover_without_witness_or_sequence",
                    "interpretation": "The issue is a failure-triage stimulus gap, not a coverage-closure request for a new directed sequence.",
                }
            )
        if (
            task_type == "failure_triage"
            and coverage
            and ("eventual" in combined_text or "fairness" in combined_text)
            and ("ready" in related_signal_text or "valid" in related_signal_text)
        ):
            cues.append(
                {
                    "kind": "stimulus_never_drives_condition",
                    "cue": "liveness_or_fairness_goal_depends_on_ready_valid_stimulus",
                    "interpretation": "A liveness/fairness-style coverage or property target depends on environment/testbench driving the ready/valid condition.",
                }
            )
        if task_type == "coverage_closure" and expected_reachable is True and (
            has_suggested_sequence or has_witness or cover_status in {"reachable", "uncovered"}
        ):
            cues.append(
                {
                    "kind": "reachable_cover_with_valid_environment",
                    "cue": "coverage_closure_reachable_goal",
                    "interpretation": "The goal is a reachable coverage closure target with a valid environment and should use directed sequence generation.",
                }
            )

    if is_invalid:
        triage_direction = "unreachable_or_invalid_coverage_goal"
    elif any(
        cue["kind"]
        in {
            "missing_required_stimulus",
            "cover_goal_unhit_because_stimulus_absent",
            "stimulus_never_drives_condition",
        }
        for cue in cues
    ):
        triage_direction = "testbench_stimulus_bug"
    elif any(cue["kind"] == "reachable_cover_with_valid_environment" for cue in cues):
        triage_direction = "reachable_coverage_gap"
    else:
        triage_direction = "unknown"

    reason = ""
    if triage_direction == "testbench_stimulus_bug":
        reason = "Evidence indicates missing or insufficient testbench stimulus rather than a request for a new coverage-closure sequence."
    elif triage_direction == "reachable_coverage_gap":
        reason = "Evidence indicates a reachable coverage goal with a valid environment, suitable for directed coverage closure."
    elif triage_direction == "unreachable_or_invalid_coverage_goal":
        reason = "Evidence indicates the coverage goal is invalid or unreachable."

    return {
        "requires_stimulus_review": bool(cues),
        "triage_direction": triage_direction,
        "coverage_goal": coverage.get("coverage_goal"),
        "expected_test_hits": expected_hits,
        "expected_reachable": expected_reachable,
        "expected_cover_status": coverage.get("expected_cover_status"),
        "has_suggested_sequence": has_suggested_sequence,
        "has_witness_events": has_witness,
        "risk_cues": cues,
        "reason": reason,
    }


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
