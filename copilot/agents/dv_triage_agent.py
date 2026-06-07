#!/usr/bin/env python3
"""DV triage agent.

The agent can use a configured LLM backend (`JASPERLOOP_LLM_CMD`) or a
deterministic structured fallback. The fallback intentionally does not read
`gold_label`; it uses only evidence-packet fields available to an agent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from copilot.json_utils import coerce_string_list
from copilot.llm_client import call_llm_json, llm_configured
from copilot.playbook_guidance import prompt_guidance_refs

ACTION_BY_ISSUE = {
    "rtl_design_bug": "fix_rtl",
    "assertion_property_bug": "fix_assertion_property",
    "assumption_constraint_bug": "fix_assumption_constraint",
    "testbench_stimulus_bug": "fix_testbench_or_stimulus",
    "reachable_coverage_gap": "add_directed_test_or_sequence",
    "unreachable_or_invalid_coverage_goal": "prove_unreachable_or_waive_coverage_goal",
}

ALLOWED_ISSUES = set(ACTION_BY_ISSUE)


def diagnose(
    packet: dict[str, object],
    use_llm: bool = False,
    llm_command: str | None = None,
) -> dict[str, object]:
    if use_llm or llm_configured(llm_command):
        try:
            response = call_llm_json(build_prompt(packet), llm_command)
            return normalize_diagnosis(packet, response.json_object)
        except Exception as exc:  # noqa: BLE001 - fallback is intentional for demos.
            fallback = structured_fallback(packet)
            fallback["llm_error"] = str(exc)
            return fallback
    return structured_fallback(packet)


def structured_fallback(packet: dict[str, object]) -> dict[str, object]:
    case_id = str(packet.get("case_id", "unknown"))
    issue_type = infer_issue_type(packet)
    action = ACTION_BY_ISSUE.get(issue_type, "rerun_jaspergold")
    root = infer_root_cause(packet, issue_type)

    return {
        "source": "structured_fallback",
        "case_id": case_id,
        "predicted_issue_type": issue_type,
        "root_cause_ranked": [
            {
                "rank": 1,
                "hypothesis": root,
                "evidence": collect_evidence(packet, issue_type),
            }
        ],
        "suspect_rtl_signals": infer_suspect_signals(packet),
        "suspect_assertions_or_assumptions": infer_suspect_properties(packet),
        "recommended_next_action": action,
        "debug_checklist": [
            "Inspect JasperGold property status.",
            "Review counterexample signal transitions.",
            "Check assertion and assumption intent.",
            "Rerun JasperGold after the proposed fix.",
        ],
    }


def infer_issue_type(packet: dict[str, object]) -> str:
    text = json.dumps(heuristic_packet(packet)).lower()
    task_type = str(packet.get("task_type", ""))
    variant = str(packet.get("variant", ""))
    coverage = packet.get("coverage_context", {})
    failing_property = packet.get("failing_property", {})
    vacuity = packet.get("vacuity_context", {})
    property_id = ""
    if isinstance(failing_property, dict):
        property_id = str(failing_property.get("property_id", "")).lower()

    if assumption_constraint_priority(packet):
        return "assumption_constraint_bug"
    if isinstance(vacuity, dict) and (
        vacuity.get("vacuity_status") == "vacuous" or vacuity.get("vacuous_properties")
    ):
        return "assumption_constraint_bug"
    if "overconstrain" in text or "unreachable antecedent" in text:
        return "assumption_constraint_bug"

    stimulus_direction = stimulus_coverage_direction(packet)
    if stimulus_direction == "testbench_stimulus_bug":
        return "testbench_stimulus_bug"
    if stimulus_direction == "unreachable_or_invalid_coverage_goal":
        return "unreachable_or_invalid_coverage_goal"
    if stimulus_direction == "reachable_coverage_gap":
        return "reachable_coverage_gap"

    if isinstance(coverage, dict) and coverage:
        expected_reachable = coverage.get("expected_reachable")
        cover_status = str(coverage.get("expected_cover_status", "")).lower()
        if expected_reachable is False or cover_status == "unreachable":
            return "unreachable_or_invalid_coverage_goal"
        if task_type == "coverage_closure":
            return "reachable_coverage_gap"
        if "simulation" in text or "stimulus" in text or "testbench" in text:
            return "testbench_stimulus_bug"
        return "reachable_coverage_gap"

    if property_id.endswith("_bad") or "_bad" in property_id:
        return "assertion_property_bug"
    if variant.startswith("bug_"):
        return "rtl_design_bug"
    if "testbench" in text or "stimulus" in text:
        return "testbench_stimulus_bug"
    if "omits" in text or "incorrectly" in text or "property assumes" in text:
        return "assertion_property_bug"
    return "assertion_property_bug"


def infer_root_cause(packet: dict[str, object], issue_type: str) -> str:
    cex = packet.get("counterexample_summary", {})
    if isinstance(cex, dict) and cex.get("first_suspicious_observation"):
        observation = str(cex["first_suspicious_observation"])
    else:
        observation = "JasperGold and manifest context identify the likely failure owner."

    if issue_type == "rtl_design_bug":
        return "The RTL variant is inconsistent with the property intent. " + observation
    if issue_type == "assertion_property_bug":
        return "The assertion intent is broader or different from the design specification."
    if issue_type == "assumption_constraint_bug":
        return "An active assumption or constraint removes behavior required by the property or coverage goal."
    if issue_type == "testbench_stimulus_bug":
        return "The design behavior is reachable, but the stimulus does not exercise the required scenario."
    if issue_type == "reachable_coverage_gap":
        return "Benchmark metadata labels the goal as reachable, so closure needs directed stimulus."
    return "The goal contradicts the design intent or is unreachable under valid constraints."


def collect_evidence(packet: dict[str, object], issue_type: str) -> list[str]:
    evidence = []
    cex = packet.get("counterexample_summary", {})
    if isinstance(cex, dict):
        observation = cex.get("first_suspicious_observation")
        if observation:
            evidence.append(str(observation))
        events = cex.get("semantic_events") or cex.get("events")
        if isinstance(events, list) and events:
            evidence.append(str(events[0]))

    jasper = packet.get("jasper_result", {})
    if isinstance(jasper, dict):
        summary = jasper.get("summary", {})
        if isinstance(summary, dict) and summary.get("falsified_properties"):
            evidence.append("Falsified properties: " + ", ".join(coerce_string_list(summary["falsified_properties"])))

    coverage = packet.get("coverage_context", {})
    if isinstance(coverage, dict) and coverage:
        if coverage.get("expected_cover_status"):
            evidence.append(f"Expected cover status: {coverage.get('expected_cover_status')}")
        if coverage.get("expected_reachable") is not None:
            evidence.append(f"Expected reachable: {coverage.get('expected_reachable')}")

    stimulus = packet.get("stimulus_context", {})
    if issue_type in {"testbench_stimulus_bug", "reachable_coverage_gap", "unreachable_or_invalid_coverage_goal"} and isinstance(stimulus, dict):
        reason = stimulus.get("reason")
        if reason:
            evidence.append(str(reason))
        cues = stimulus.get("risk_cues")
        if isinstance(cues, list):
            for cue in cues[:2]:
                if isinstance(cue, dict) and cue.get("interpretation"):
                    evidence.append(str(cue["interpretation"]))

    assumptions = packet.get("active_assumptions", [])
    if isinstance(assumptions, list) and assumptions:
        ids = [str(item.get("id")) for item in assumptions if isinstance(item, dict) and item.get("id")]
        if ids:
            evidence.append("Active assumptions under suspicion: " + ", ".join(ids))

    vacuity = packet.get("vacuity_context", {})
    if issue_type == "assumption_constraint_bug" and isinstance(vacuity, dict):
        reason = vacuity.get("reason")
        if reason:
            evidence.append(str(reason))
        cues = vacuity.get("assumption_risk_cues")
        if isinstance(cues, list):
            for cue in cues[:2]:
                if isinstance(cue, dict) and cue.get("interpretation"):
                    evidence.append(str(cue["interpretation"]))

    if not evidence:
        evidence.append(f"Structured fallback classified this packet as {issue_type}.")
    return evidence[:5]


def infer_suspect_signals(packet: dict[str, object]) -> list[str]:
    cex = packet.get("counterexample_summary", {})
    if isinstance(cex, dict):
        changed = cex.get("changed_signals")
        if isinstance(changed, list):
            return [str(signal) for signal in changed[:8]]
    coverage = packet.get("coverage_context", {})
    if isinstance(coverage, dict) and isinstance(coverage.get("related_signals"), list):
        return [str(signal) for signal in coverage["related_signals"][:8]]
    return []


def allowed_signal_names(packet: dict[str, object]) -> set[str]:
    allowed: set[str] = set()
    signal_role_map = packet.get("signal_role_map")
    if isinstance(signal_role_map, dict):
        allowed.update(str(signal) for signal in signal_role_map)

    cex = packet.get("counterexample_summary")
    if isinstance(cex, dict):
        allowed.update(coerce_string_list(cex.get("changed_signals")))

    coverage = packet.get("coverage_context")
    if isinstance(coverage, dict):
        allowed.update(coerce_string_list(coverage.get("related_signals")))

    coverage_evidence = packet.get("coverage_evidence")
    if isinstance(coverage_evidence, dict):
        allowed.update(coerce_string_list(coverage_evidence.get("related_signals")))
    return allowed


def filter_allowed_signals(packet: dict[str, object], signals: object) -> tuple[list[str], list[str]]:
    allowed = allowed_signal_names(packet)
    kept: list[str] = []
    dropped: list[str] = []
    for signal in coerce_string_list(signals):
        if signal in allowed:
            kept.append(signal)
        elif signal:
            dropped.append(signal)
    return kept, dropped


def infer_suspect_properties(packet: dict[str, object]) -> list[str]:
    suspects = []
    failing_property = packet.get("failing_property", {})
    if isinstance(failing_property, dict) and failing_property.get("property_id"):
        suspects.append(str(failing_property["property_id"]))
    assumptions = packet.get("active_assumptions", [])
    if isinstance(assumptions, list):
        for item in assumptions:
            if isinstance(item, dict) and item.get("id"):
                suspects.append(str(item["id"]))
    return suspects


def build_prompt(packet: dict[str, object]) -> str:
    payload = sanitized_packet(packet)
    allowed_signals = sorted(allowed_signal_names(packet))
    assumption_hints = assumption_vacuity_prompt_hints(packet)
    stimulus_hints = stimulus_vs_coverage_prompt_hints(packet)
    return (
        "You are JasperLoop-DV, a formal-aware DV triage assistant. "
        "Classify the issue using only the evidence packet. Do not invent signals. "
        "Use only predicted_issue_type and recommended_next_action values allowed by "
        "diagnosis_output.schema.json. suspect_rtl_signals must come from the allowed "
        "signal list below. If no allowed signal is directly supported by evidence, "
        "return an empty suspect_rtl_signals list. Do not use natural-language labels, "
        "coverage concepts, helper names, or inferred protocol phases as signal names; "
        "for example, do not emit access or valid_addr unless they are in ALLOWED_SIGNALS. "
        "If the RTL variant is marked correct and the property intent contradicts the "
        "design intent, prefer assertion_property_bug over rtl_design_bug unless the "
        "packet provides concrete RTL signal evidence. If ASSUMPTION_VACUITY_TRIAGE_HINTS "
        "contains blocking assumptions, reset-stuck assumptions, missing environment "
        "constraints, or vacuous properties, review assumption_constraint_bug before "
        "assertion_property_bug. When your hypothesis or evidence says an assumption "
        "or constraint removes, blocks, allows impossible, or underconstrains required "
        "behavior, predicted_issue_type must be assumption_constraint_bug and "
        "recommended_next_action must be fix_assumption_constraint. If STIMULUS_VS_COVERAGE_HINTS "
        "indicates missing or insufficient stimulus, prefer testbench_stimulus_bug and "
        "fix_testbench_or_stimulus. If formal cover/witness or a directed sequence shows "
        "a reachable goal with a valid environment, prefer reachable_coverage_gap and "
        "add_directed_test_or_sequence. If the goal is illegal, invalid, or unreachable, "
        "prefer unreachable_or_invalid_coverage_goal. Do not classify a stimulus bug as "
        "coverage closure merely because a coverage goal is unhit. Return exactly one JSON object "
        "matching diagnosis_output.schema.json; no Markdown, comments, code fences, "
        "or explanations outside the JSON object.\n\n"
        "ALLOWED_SIGNALS:\n"
        + json.dumps(allowed_signals, indent=2)
        + "\n\n"
        "ASSUMPTION_VACUITY_TRIAGE_HINTS:\n"
        + json.dumps(assumption_hints, indent=2)
        + "\n\n"
        "STIMULUS_VS_COVERAGE_HINTS:\n"
        + json.dumps(stimulus_hints, indent=2)
        + "\n\n"
        "PLAYBOOK_GUIDANCE:\n"
        + prompt_guidance_refs(
            "CEX debug checklist",
            "assumption/vacuity review checklist",
            "intent alignment review note",
        )
        + "\n\n"
        + json.dumps(payload, indent=2)
    )


def sanitized_packet(packet: dict[str, object]) -> dict[str, object]:
    clone = dict(packet)
    clone.pop("gold_label", None)
    failing_property = clone.get("failing_property")
    if isinstance(failing_property, dict):
        failing_property = dict(failing_property)
        failing_property.pop("expected_issue_type", None)
        clone["failing_property"] = failing_property
    return clone


def heuristic_packet(packet: dict[str, object]) -> dict[str, object]:
    clone = sanitized_packet(packet)
    clone.pop("allowed_issue_types", None)
    clone.pop("allowed_next_actions", None)
    return clone


def normalize_diagnosis(packet: dict[str, object], output: dict[str, object]) -> dict[str, object]:
    issue = str(output.get("predicted_issue_type", ""))
    if issue not in ALLOWED_ISSUES:
        issue = infer_issue_type(packet)
    action = str(output.get("recommended_next_action", ""))
    if action not in set(ACTION_BY_ISSUE.values()):
        action = ACTION_BY_ISSUE[issue]
    normalized_notes = []
    if should_normalize_to_assumption_constraint(packet, output, issue, action):
        issue = "assumption_constraint_bug"
        action = ACTION_BY_ISSUE[issue]
        normalized_notes.append(
            "Aligned issue/action with assumption/vacuity evidence: use "
            "assumption_constraint_bug and fix_assumption_constraint."
        )
    if should_normalize_to_testbench_stimulus(packet, output, issue, action):
        issue = "testbench_stimulus_bug"
        action = ACTION_BY_ISSUE[issue]
        normalized_notes.append(
            "Aligned issue/action with stimulus-vs-coverage evidence: use "
            "testbench_stimulus_bug and fix_testbench_or_stimulus."
        )
    roots = output.get("root_cause_ranked")
    if not isinstance(roots, list) or not roots:
        roots = structured_fallback(packet)["root_cause_ranked"]
    suspect_signals, dropped_signals = filter_allowed_signals(packet, output.get("suspect_rtl_signals"))
    debug_checklist = coerce_string_list(output.get("debug_checklist")) or structured_fallback(packet)["debug_checklist"]
    if dropped_signals:
        debug_checklist = [
            *debug_checklist,
            "Dropped unsupported suspect_rtl_signals: " + ", ".join(sorted(dropped_signals)),
        ]
    if normalized_notes:
        debug_checklist = [*debug_checklist, *normalized_notes]
    return {
        "source": "llm",
        "case_id": str(output.get("case_id", packet.get("case_id", "unknown"))),
        "predicted_issue_type": issue,
        "root_cause_ranked": roots,
        "suspect_rtl_signals": suspect_signals,
        "suspect_assertions_or_assumptions": coerce_string_list(
            output.get("suspect_assertions_or_assumptions")
        ),
        "recommended_next_action": action,
        "debug_checklist": debug_checklist,
    }


def assumption_constraint_priority(packet: dict[str, object]) -> bool:
    vacuity = packet.get("vacuity_context")
    if not isinstance(vacuity, dict):
        return False
    if vacuity.get("vacuity_status") == "vacuous" or vacuity.get("vacuous_properties"):
        return True
    if vacuity.get("constraint_direction") in {"overconstraint", "underconstraint"}:
        return True
    cues = vacuity.get("assumption_risk_cues")
    return isinstance(cues, list) and bool(cues)


def assumption_vacuity_prompt_hints(packet: dict[str, object]) -> dict[str, object]:
    vacuity = packet.get("vacuity_context")
    if not isinstance(vacuity, dict):
        return {
            "requires_assumption_review": False,
            "constraint_direction": "unknown",
            "risk_cues": [],
        }
    return {
        "requires_assumption_review": bool(vacuity.get("requires_assumption_review")),
        "constraint_direction": vacuity.get("constraint_direction", "unknown"),
        "suspect_assumptions": vacuity.get("suspect_assumptions", []),
        "reason": vacuity.get("reason", ""),
        "risk_cues": vacuity.get("assumption_risk_cues", []),
        "classification_rule": (
            "If these cues explain the failure, classify as assumption_constraint_bug "
            "with recommended_next_action fix_assumption_constraint."
        ),
    }


def stimulus_coverage_direction(packet: dict[str, object]) -> str:
    stimulus = packet.get("stimulus_context")
    if not isinstance(stimulus, dict):
        return "unknown"
    direction = str(stimulus.get("triage_direction", "unknown"))
    if direction in {
        "testbench_stimulus_bug",
        "reachable_coverage_gap",
        "unreachable_or_invalid_coverage_goal",
    }:
        return direction
    return "unknown"


def stimulus_vs_coverage_prompt_hints(packet: dict[str, object]) -> dict[str, object]:
    stimulus = packet.get("stimulus_context")
    if not isinstance(stimulus, dict):
        return {
            "requires_stimulus_review": False,
            "triage_direction": "unknown",
            "risk_cues": [],
        }
    return {
        "requires_stimulus_review": bool(stimulus.get("requires_stimulus_review")),
        "triage_direction": stimulus.get("triage_direction", "unknown"),
        "coverage_goal": stimulus.get("coverage_goal"),
        "expected_test_hits": stimulus.get("expected_test_hits"),
        "expected_reachable": stimulus.get("expected_reachable"),
        "has_suggested_sequence": stimulus.get("has_suggested_sequence", False),
        "has_witness_events": stimulus.get("has_witness_events", False),
        "reason": stimulus.get("reason", ""),
        "risk_cues": stimulus.get("risk_cues", []),
        "classification_rule": (
            "Missing stimulus or environment driving maps to testbench_stimulus_bug. "
            "Reachable cover with a valid environment maps to reachable_coverage_gap. "
            "Illegal or unreachable cover maps to unreachable_or_invalid_coverage_goal."
        ),
    }


def should_normalize_to_assumption_constraint(
    packet: dict[str, object],
    output: dict[str, object],
    issue: str,
    action: str,
) -> bool:
    if (
        issue == "assumption_constraint_bug"
        and action == ACTION_BY_ISSUE["assumption_constraint_bug"]
    ):
        return False
    if not assumption_constraint_priority(packet):
        return False
    vacuity = packet.get("vacuity_context")
    if isinstance(vacuity, dict) and vacuity.get("constraint_direction") in {
        "overconstraint",
        "underconstraint",
    }:
        return True
    output_text = json.dumps(output, sort_keys=True).lower()
    evidence_terms = (
        "assumption",
        "constraint",
        "overconstrain",
        "underconstrain",
        "vacuous",
        "vacuity",
        "unreachable",
        "removes",
        "blocks",
        "forbids",
        "forces",
        "missing environment",
        "environment contract",
    )
    return any(term in output_text for term in evidence_terms)


def should_normalize_to_testbench_stimulus(
    packet: dict[str, object],
    output: dict[str, object],
    issue: str,
    action: str,
) -> bool:
    if issue == "testbench_stimulus_bug" and action == ACTION_BY_ISSUE["testbench_stimulus_bug"]:
        return False
    if stimulus_coverage_direction(packet) != "testbench_stimulus_bug":
        return False
    if issue not in {"reachable_coverage_gap", "assertion_property_bug"}:
        return False
    output_text = json.dumps(output, sort_keys=True).lower()
    evidence_terms = (
        "stimulus",
        "testbench",
        "sequence",
        "drive",
        "drives",
        "assert",
        "asserts",
        "ready",
        "valid",
        "unhit",
        "not hit",
        "not exercise",
    )
    return any(term in output_text for term in evidence_terms)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--prompt-out", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    packet = json.loads(args.packet.read_text())
    if args.prompt_out:
        args.prompt_out.parent.mkdir(parents=True, exist_ok=True)
        args.prompt_out.write_text(build_prompt(packet) + "\n")
    output = diagnose(packet, use_llm=args.llm, llm_command=args.llm_command)
    text = json.dumps(output, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
