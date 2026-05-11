#!/usr/bin/env python3
"""Coverage closure agent with pluggable LLM backend and deterministic fallback."""

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


def recommend(
    packet: dict[str, object],
    use_llm: bool = False,
    llm_command: str | None = None,
) -> dict[str, object]:
    if use_llm or llm_configured(llm_command):
        try:
            response = call_llm_json(build_prompt(packet), llm_command)
            return normalize_recommendation(packet, response.json_object)
        except Exception as exc:  # noqa: BLE001 - fallback is intentional for demos.
            fallback = structured_fallback(packet)
            fallback["llm_error"] = str(exc)
            return fallback
    return structured_fallback(packet)


def structured_fallback(packet: dict[str, object]) -> dict[str, object]:
    coverage = packet.get("coverage_context", {})
    if not isinstance(coverage, dict):
        coverage = {}
    evidence_packet = packet.get("coverage_evidence", {})
    if not isinstance(evidence_packet, dict):
        evidence_packet = {}
    cover_status = str(
        evidence_packet.get("expected_cover_status") or coverage.get("expected_cover_status") or ""
    ).lower()
    expected = evidence_packet.get("expected_reachable", coverage.get("expected_reachable", True))
    reachable = cover_status in {"reachable", "covered"}

    if reachable and expected:
        gap_type = "reachable_coverage_gap"
        action = "add_directed_test_or_sequence"
        evidence = collect_structured_evidence(coverage, evidence_packet, reachable=True)
    else:
        gap_type = "unreachable_or_invalid_coverage_goal"
        action = "prove_unreachable_or_waive_coverage_goal"
        evidence = collect_structured_evidence(coverage, evidence_packet, reachable=False)

    return {
        "source": "structured_fallback",
        "case_id": packet.get("case_id", "unknown"),
        "coverage_gap_type": gap_type,
        "recommended_next_action": action,
        "directed_sequence": evidence_packet.get("suggested_sequence") or coverage.get("suggested_sequence", []),
        "evidence": evidence,
    }


def collect_structured_evidence(
    coverage: dict[str, object],
    evidence_packet: dict[str, object],
    reachable: bool,
) -> list[str]:
    evidence = []
    goal = evidence_packet.get("coverage_goal") or coverage.get("coverage_goal")
    if goal:
        evidence.append(f"Coverage goal: {goal}")
    status = evidence_packet.get("expected_cover_status") or coverage.get("expected_cover_status")
    if status:
        evidence.append(f"Expected cover status: {status}")
    expected = evidence_packet.get("expected_reachable", coverage.get("expected_reachable"))
    if expected is not None:
        evidence.append(f"Expected reachable: {expected}")
    expression = evidence_packet.get("expression") or coverage.get("expression")
    if expression:
        evidence.append(f"Coverage expression: {expression}")
    witness_events = evidence_packet.get("witness_events")
    if isinstance(witness_events, list) and witness_events:
        evidence.append("Witness trace starts with: " + str(witness_events[0]))
    if not evidence:
        evidence.append(
            "Benchmark metadata labels the goal as reachable."
            if reachable
            else "Coverage goal is unreachable, invalid, or contradicts expected behavior."
        )
    return evidence[:5]


def build_prompt(packet: dict[str, object]) -> str:
    return (
        "You are JasperLoop-DV, a formal-aware coverage closure assistant. "
        "Use cover reachability, coverage intent, assumptions, and related signals. "
        "Return JSON with coverage_gap_type, recommended_next_action, directed_sequence, and evidence.\n\n"
        "PLAYBOOK_GUIDANCE:\n"
        + prompt_guidance_refs(
            "coverage closure decision checklist",
            "assumption/vacuity review checklist",
            "intent alignment review note",
        )
        + "\n\n"
        + json.dumps(sanitized_packet(packet), indent=2)
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


def normalize_recommendation(packet: dict[str, object], output: dict[str, object]) -> dict[str, object]:
    fallback = structured_fallback(packet)
    gap_type = str(output.get("coverage_gap_type", ""))
    if gap_type not in {"reachable_coverage_gap", "unreachable_or_invalid_coverage_goal"}:
        gap_type = str(fallback["coverage_gap_type"])
    action = str(output.get("recommended_next_action", ""))
    if action not in {
        "add_directed_test_or_sequence",
        "prove_unreachable_or_waive_coverage_goal",
        "fix_assumption_constraint",
        "rerun_jaspergold",
    }:
        action = (
            "add_directed_test_or_sequence"
            if gap_type == "reachable_coverage_gap"
            else "prove_unreachable_or_waive_coverage_goal"
        )
    return {
        "source": "llm",
        "case_id": str(output.get("case_id", packet.get("case_id", "unknown"))),
        "coverage_gap_type": gap_type,
        "recommended_next_action": action,
        "directed_sequence": coerce_string_list(output.get("directed_sequence"))
        or coerce_string_list(fallback.get("directed_sequence")),
        "evidence": coerce_string_list(output.get("evidence"))
        or coerce_string_list(fallback.get("evidence")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument("--llm-command")
    parser.add_argument("--prompt-out", type=Path)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text())
    if args.prompt_out:
        args.prompt_out.parent.mkdir(parents=True, exist_ok=True)
        args.prompt_out.write_text(build_prompt(packet) + "\n")
    print(json.dumps(recommend(packet, use_llm=args.llm, llm_command=args.llm_command), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
