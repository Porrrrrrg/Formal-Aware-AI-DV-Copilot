#!/usr/bin/env python3
"""Simple non-LLM heuristic baseline for diagnosis cases.

This baseline is intentionally shallow. It uses only packet metadata that a
debug script could inspect directly and never reads gold labels.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

ACTION_BY_ISSUE = {
    "rtl_design_bug": "fix_rtl",
    "assertion_property_bug": "fix_assertion_property",
    "assumption_constraint_bug": "fix_assumption_constraint",
    "testbench_stimulus_bug": "fix_testbench_or_stimulus",
    "reachable_coverage_gap": "add_directed_test_or_sequence",
    "unreachable_or_invalid_coverage_goal": "prove_unreachable_or_waive_coverage_goal",
}


def predict(packet: dict[str, object]) -> dict[str, object]:
    issue = infer_issue_type(packet)
    return {
        "source": "heuristic",
        "case_id": str(packet.get("case_id", "unknown")),
        "predicted_issue_type": issue,
        "root_cause_ranked": [
            {
                "rank": 1,
                "hypothesis": "Rule-based baseline prediction from packet metadata.",
                "evidence": ["Heuristic baseline does not use an LLM or gold labels."],
            }
        ],
        "suspect_rtl_signals": [],
        "suspect_assertions_or_assumptions": [],
        "recommended_next_action": ACTION_BY_ISSUE[issue],
        "debug_checklist": ["Review the full structured evidence packet."],
    }


def infer_issue_type(packet: dict[str, object]) -> str:
    text = json.dumps(sanitized_packet(packet)).lower()
    variant = str(packet.get("variant", ""))
    task_type = str(packet.get("task_type", ""))
    coverage = packet.get("coverage_context", {})
    active_assumptions = packet.get("active_assumptions", [])
    failing_property = packet.get("failing_property", {})
    property_id = ""
    if isinstance(failing_property, dict):
        property_id = str(failing_property.get("property_id", "")).lower()

    if isinstance(active_assumptions, list) and active_assumptions:
        return "assumption_constraint_bug"
    if "vacuous" in text or "overconstrain" in text:
        return "assumption_constraint_bug"

    if isinstance(coverage, dict) and coverage:
        if coverage.get("expected_reachable") is False:
            return "unreachable_or_invalid_coverage_goal"
        if str(coverage.get("expected_cover_status", "")).lower() == "unreachable":
            return "unreachable_or_invalid_coverage_goal"
        if task_type == "coverage_closure":
            return "reachable_coverage_gap"
        if "testbench" in text or "stimulus" in text:
            return "testbench_stimulus_bug"
        return "reachable_coverage_gap"

    if property_id.endswith("_bad") or "_bad" in property_id:
        return "assertion_property_bug"
    if "missing" in property_id or "unconditional" in property_id:
        return "assertion_property_bug"
    if variant.startswith("bug_"):
        return "rtl_design_bug"
    if "testbench" in text or "stimulus" in text:
        return "testbench_stimulus_bug"
    return "rtl_design_bug"


def sanitized_packet(packet: dict[str, object]) -> dict[str, object]:
    clone = dict(packet)
    clone.pop("gold_label", None)
    clone.pop("allowed_issue_types", None)
    clone.pop("allowed_next_actions", None)
    failing_property = clone.get("failing_property")
    if isinstance(failing_property, dict):
        failing_property = dict(failing_property)
        failing_property.pop("expected_issue_type", None)
        clone["failing_property"] = failing_property
    return clone


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    print(json.dumps(predict(json.loads(args.packet.read_text())), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
