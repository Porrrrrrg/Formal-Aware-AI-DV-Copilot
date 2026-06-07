from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from copilot.agents.rtl_repair_agent import build_prompt, propose_rtl_repair

ROOT = Path(__file__).resolve().parents[1]


def manifest() -> dict[str, object]:
    return {
        "schema_version": "rtl_project_manifest_v1",
        "design_id": "tiny",
        "rtl_files": ["rtl/tiny.sv"],
        "top_module": "tiny",
    }


def bundle(next_owner: str = "rtl") -> dict[str, object]:
    return {
        "schema_version": "formal_debug_bundle_v1",
        "repair_recommendation": {"next_owner": next_owner, "reason": "evidence"},
    }


def test_rtl_repair_prompt_refuses_non_rtl_patch() -> None:
    prompt = build_prompt(
        rtl_project_manifest=manifest(),
        formal_debug_bundle=bundle("sva"),
        stable_sva={"property_id": "p0"},
        counterexample_summary={},
        triage={"predicted_issue_type": "assertion_property_bug"},
        suspect_signals=[],
        suspect_rtl_slices=[],
        active_assumptions=[],
        prior_proven_properties=[],
        allowed_patch_files=["rtl/tiny.sv"],
    )

    assert "issue_type=rtl_design_bug" in prompt
    assert "empty" in prompt
    assert "Do not modify SVA" in prompt


def test_non_rtl_triage_returns_empty_patch_candidate() -> None:
    candidate = propose_rtl_repair(
        rtl_project_manifest=manifest(),
        formal_debug_bundle=bundle("sva"),
        stable_sva={"property_id": "p0"},
        triage={"predicted_issue_type": "assertion_property_bug"},
        allowed_patch_files=["rtl/tiny.sv"],
    )

    assert candidate["issue_type"] == "assertion_property_bug"
    assert candidate["unified_diff"] == ""
    assert candidate["requires_recheck"] is False


def test_rtl_repair_candidate_schema_accepts_agent_output() -> None:
    schema = json.loads(
        (ROOT / "copilot" / "schemas" / "rtl_repair_candidate.schema.json").read_text(
            encoding="utf-8"
        )
    )
    candidate = propose_rtl_repair(
        rtl_project_manifest=manifest(),
        formal_debug_bundle=bundle("rtl"),
        stable_sva={"property_id": "p0"},
        triage={"predicted_issue_type": "rtl_design_bug"},
        suspect_signals=["gnt0"],
        allowed_patch_files=["rtl/tiny.sv"],
    )

    Draft202012Validator(schema).validate(candidate)
    assert candidate["issue_type"] == "rtl_design_bug"
    assert candidate["requires_recheck"] is True
