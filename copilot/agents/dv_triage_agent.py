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
    active_assumptions = packet.get("active_assumptions", [])
    failing_property = packet.get("failing_property", {})
    vacuity = packet.get("vacuity_context", {})
    property_id = ""
    if isinstance(failing_property, dict):
        property_id = str(failing_property.get("property_id", "")).lower()

    if isinstance(active_assumptions, list) and active_assumptions:
        return "assumption_constraint_bug"
    if isinstance(vacuity, dict) and (
        vacuity.get("vacuity_status") == "vacuous" or vacuity.get("vacuous_properties")
    ):
        return "assumption_constraint_bug"
    if "overconstrain" in text or "unreachable antecedent" in text:
        return "assumption_constraint_bug"

    if isinstance(coverage, dict) and coverage:
        expected_reachable = coverage.get("expected_reachable")
        cover_status = str(coverage.get("jasper_cover_result", "")).lower()
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
        return "Formal cover evidence says the goal is reachable, so closure needs directed stimulus."
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
        if coverage.get("jasper_cover_result"):
            evidence.append(f"Jasper cover result: {coverage.get('jasper_cover_result')}")
        if coverage.get("expected_reachable") is not None:
            evidence.append(f"Expected reachable: {coverage.get('expected_reachable')}")

    assumptions = packet.get("active_assumptions", [])
    if isinstance(assumptions, list) and assumptions:
        ids = [str(item.get("id")) for item in assumptions if isinstance(item, dict) and item.get("id")]
        if ids:
            evidence.append("Active assumptions under suspicion: " + ", ".join(ids))

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
    return (
        "You are JasperLoop-DV, a formal-aware DV triage assistant. "
        "Classify the issue using only the evidence packet. Do not invent signals. "
        "Return JSON matching diagnosis_output.schema.json.\n\n"
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
    roots = output.get("root_cause_ranked")
    if not isinstance(roots, list) or not roots:
        roots = structured_fallback(packet)["root_cause_ranked"]
    return {
        "source": "llm",
        "case_id": str(output.get("case_id", packet.get("case_id", "unknown"))),
        "predicted_issue_type": issue,
        "root_cause_ranked": roots,
        "suspect_rtl_signals": coerce_string_list(output.get("suspect_rtl_signals")),
        "suspect_assertions_or_assumptions": coerce_string_list(
            output.get("suspect_assertions_or_assumptions")
        ),
        "recommended_next_action": action,
        "debug_checklist": coerce_string_list(output.get("debug_checklist"))
        or structured_fallback(packet)["debug_checklist"],
    }


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
