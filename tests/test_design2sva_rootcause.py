from __future__ import annotations

import json
from pathlib import Path

from copilot.agents.design2sva_rootcause import (
    CANDIDATE_GENERATION_FAILURE,
    COVER_GENERATION_BUG,
    DESIGN2SVA_EMBEDDING_BUG,
    JASPER_PARSER_MISCLASSIFICATION,
    NATIVE_HARNESS_UNREACHABLE,
    REFERENCE_TASK_INVALID,
    RESET_CLOCK_MISMATCH,
    ROOT_CAUSE_LABELS,
    UNKNOWN,
    classify_root_cause_candidate,
    summarize_root_cause_candidates,
)


def proven_native_oracle() -> dict[str, object]:
    return {
        "reference_proven": True,
        "reference_non_vacuous": True,
        "reference_antecedent_reachable": True,
        "harness_reachability_status": "reachable",
        "reference_proof_metadata": {
            "status": "passed",
            "syntax_status": "passed",
            "proof_status": "proven",
            "vacuity_status": "not_flagged_vacuous",
        },
    }


def test_native_unreachable_precedes_candidate_diagnostics() -> None:
    row = {
        "source": "llm",
        "reset_clock_mismatch": True,
        "failure_category": "reset_clock_mismatch",
    }
    native = {
        "harness_reachability_status": "unreachable",
        "reference_antecedent_metadata": {"antecedent_reachability": "unreachable"},
    }

    assert classify_root_cause_candidate(row, native) == NATIVE_HARNESS_UNREACHABLE


def test_reference_task_invalid_for_bad_native_reference() -> None:
    native = {
        "reference_syntax_ok": False,
        "harness_reachability_status": "syntax_error",
        "reference_proof_metadata": {"syntax_status": "syntax_error"},
    }

    assert (
        classify_root_cause_candidate({"source": "reference_oracle"}, native)
        == REFERENCE_TASK_INVALID
    )


def test_native_proves_but_reference_embedding_fails() -> None:
    row = {
        "source": "reference_oracle",
        "failure_category": "unreachable_antecedent",
        "proof_metadata": {
            "status": "failed",
            "syntax_status": "passed",
            "proof_status": "unreachable",
            "vacuity_status": None,
        },
        "antecedent_metadata": {
            "extraction_status": "extracted",
            "antecedent_reachability": "unreachable",
            "cover_status": "unreachable",
        },
    }

    assert classify_root_cause_candidate(row, proven_native_oracle()) == DESIGN2SVA_EMBEDDING_BUG


def test_reset_clock_mismatch_diagnostic() -> None:
    assert (
        classify_root_cause_candidate({"metrics": {"reset_clock_mismatch": True}})
        == RESET_CLOCK_MISMATCH
    )
    assert (
        classify_root_cause_candidate({"failure_category": "reset_clock_mismatch"})
        == RESET_CLOCK_MISMATCH
    )


def test_cover_generation_bug_for_unreachable_generated_cover() -> None:
    row = {
        "failure_category": "unreachable_cover_goal",
        "antecedent_metadata": {
            "extraction_status": "unconditional",
            "antecedent_reachability": "unreachable",
            "cover_status": "unreachable",
        },
    }

    assert classify_root_cause_candidate(row) == COVER_GENERATION_BUG


def test_jasper_parser_status_contradiction() -> None:
    row = {
        "proof_metadata": {
            "status": "passed",
            "syntax_status": "passed",
            "proof_status": "falsified",
            "vacuity_status": "not_flagged_vacuous",
        }
    }

    assert classify_root_cause_candidate(row) == JASPER_PARSER_MISCLASSIFICATION


def test_candidate_generation_failure_after_native_harness_proves() -> None:
    row = {
        "source": "llm",
        "failure_category": "temporal_mismatch",
        "proof_metadata": {
            "status": "failed",
            "syntax_status": "passed",
            "proof_status": "falsified",
            "vacuity_status": "not_flagged_vacuous",
        },
    }

    assert (
        classify_root_cause_candidate(row, proven_native_oracle())
        == CANDIDATE_GENERATION_FAILURE
    )


def test_unknown_when_no_stage11_rule_matches() -> None:
    assert classify_root_cause_candidate({"proof_metadata": {"status": "not_run"}}) == UNKNOWN


def test_summary_counts_can_use_case_indexed_native_oracles() -> None:
    rows = [
        {
            "case_id": "a",
            "source": "llm",
            "failure_category": "temporal_mismatch",
            "proof_metadata": {"proof_status": "falsified", "syntax_status": "passed"},
        },
        {"case_id": "b", "failure_category": "reset_clock_mismatch"},
        {"case_id": "c", "proof_metadata": {"status": "not_run"}},
    ]
    counts = summarize_root_cause_candidates(
        rows,
        native_oracle_by_case={"a": proven_native_oracle()},
        include_zero=True,
    )

    assert set(counts) == set(ROOT_CAUSE_LABELS)
    assert counts[CANDIDATE_GENERATION_FAILURE] == 1
    assert counts[RESET_CLOCK_MISMATCH] == 1
    assert counts[UNKNOWN] == 1
    assert counts[NATIVE_HARNESS_UNREACHABLE] == 0


def test_stage11_rootcause_dry_run_fixture_loads() -> None:
    fixture = json.loads(
        Path("evaluation/fixtures/design2sva_rootcause_dry_run.json").read_text(
            encoding="utf-8"
        )
    )
    rows = fixture["rows"]

    counts = summarize_root_cause_candidates(rows)

    assert counts == {RESET_CLOCK_MISMATCH: 1}
