from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
RULE_DIR = ROOT / "copilot" / "rules"

RULE_FILES = [
    "sva_repair_patterns.yaml",
    "vacuity_patterns.yaml",
    "coverage_gap_rules.yaml",
    "triage_decision_rules.yaml",
]

ALLOWED_ACTIONS = {
    "add_directed_test_or_sequence",
    "align_reset_disable_with_context",
    "align_temporal_operator_with_trace",
    "fix_assertion_property",
    "fix_assumption_constraint",
    "fix_rtl",
    "fix_testbench_or_stimulus",
    "make_minimal_syntax_edit",
    "prove_unreachable_or_waive_coverage_goal",
    "relax_or_justify_assumption",
    "repair_reset_environment",
    "require_positive_trigger_evidence",
    "rerun_jaspergold",
    "review_trigger_reachability_before_repair",
    "rewrite_trigger_or_fix_assumption",
    "add_evidence_backed_antecedent_guard",
}

REQUIRED_BOUNDARIES = {
    "proof_pass_not_intent_alignment",
    "not_flagged_vacuous_not_certificate",
    "replay_not_model_performance",
    "qwen_vs_codex_requires_manifest_parity",
    "jasperloop_not_production_signoff",
}


def test_rule_files_parse_and_have_required_shape() -> None:
    for rule_file in RULE_FILES:
        path = RULE_DIR / rule_file
        assert path.exists(), f"missing rule file: {path}"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))

        assert data["version"] == 1
        assert data["name"]
        assert data["description"]
        assert isinstance(data.get("claim_boundaries"), list)

        sections = [key for key in ("patterns", "classifications", "decisions") if key in data]
        assert len(sections) == 1
        entries = data[sections[0]]
        assert isinstance(entries, list)
        assert entries

        ids = [entry.get("id") or entry.get("issue_type") for entry in entries]
        assert len(ids) == len(set(ids))
        assert all(ids)


def test_rule_actions_match_supported_workflow_actions() -> None:
    for rule_file in RULE_FILES:
        data = yaml.safe_load((RULE_DIR / rule_file).read_text(encoding="utf-8"))
        entries = data.get("patterns") or data.get("classifications") or data.get("decisions")
        for entry in entries:
            action = entry.get("action") or entry.get("recommended_next_action")
            assert action in ALLOWED_ACTIONS


def test_rules_preserve_claim_boundaries() -> None:
    observed: set[str] = set()
    for rule_file in RULE_FILES:
        data = yaml.safe_load((RULE_DIR / rule_file).read_text(encoding="utf-8"))
        observed.update(data["claim_boundaries"])

    assert REQUIRED_BOUNDARIES <= observed
