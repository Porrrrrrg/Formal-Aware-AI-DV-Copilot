from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from copilot.agents.design2sva_repair_agent import build_prompt, repair_design2sva_candidate
from evaluation.run_design2sva_eval import row_sva_usable_for_rtl_triage

ROOT = Path(__file__).resolve().parents[1]


def task() -> dict[str, object]:
    return {
        "case_id": "case0",
        "design_id": "tiny",
        "property_id": "p0",
        "intent": "The grant output must be mutually exclusive.",
        "visible_signals": ["clk", "rst", "gnt0", "gnt1"],
        "clock_reset": {
            "clock": "clk",
            "reset": "rst",
            "clock_edge": "posedge",
            "reset_polarity": "active_high",
        },
        "helper_code_policy": {"allowed": False},
        "evaluation_metadata": {"reference_sva": "must not appear"},
    }


def context() -> dict[str, object]:
    return {
        "visible_signals": ["clk", "rst", "gnt0", "gnt1"],
        "clock_reset_candidates": {"clocks": ["clk"], "resets": ["rst"]},
        "interface": {"ports": [{"name": "clk"}, {"name": "rst"}, {"name": "gnt0"}, {"name": "gnt1"}]},
    }


def candidate() -> dict[str, object]:
    return {
        "property_id": "p0",
        "sva": "p0: assert property (@(posedge bad_clk) disable iff (!rst_n) ghost_signal);",
        "helper_code": "",
        "referenced_signals": [],
        "intent_summary": "Bad candidate.",
        "source": "test",
        "repair_metadata": {
            "round": 0,
            "failure_category": "reset_clock_mismatch",
            "feedback": "",
            "changed_by_repair": False,
        },
        "proof_metadata": {
            "backend": "jaspergold",
            "status": "not_run",
            "syntax_status": "not_run",
            "proof_status": None,
            "vacuity_status": None,
            "report_dir": None,
        },
    }


def metrics() -> dict[str, object]:
    return {
        "case_id": "case0",
        "design_id": "tiny",
        "property_id": "p0",
        "failure_category": "unknown_signal",
        "hallucinated_identifiers": ["ghost_signal", "bad_clk", "rst_n"],
        "reset_clock_mismatch": True,
        "antecedent_metadata": {"extraction_status": "invariant"},
        "antecedent_reachable": True,
        "cover_reachable": True,
        "embedding_audit": {"checks": {"clock_reset_mismatch": {"has_issue": True}}},
        "proof_metadata": {
            "backend": "jaspergold",
            "status": "not_run",
            "syntax_status": "not_run",
            "proof_status": None,
            "vacuity_status": None,
            "report_dir": None,
        },
    }


def test_design2sva_repair_prompt_omits_reference_and_includes_debug_context() -> None:
    prompt = build_prompt(
        task=task(),
        context=context(),
        current_candidate=candidate(),
        metrics=metrics(),
        formal_debug_bundle={"schema_version": "formal_debug_bundle_v1", "repair_recommendation": {"next_owner": "sva"}},
        jasper_feedback="reset mismatch feedback",
        round_index=1,
    )

    assert "formal_debug_bundle_v1" in prompt
    assert "reset mismatch feedback" in prompt
    assert "clock_reset_contract" in prompt
    assert "must not appear" not in prompt
    assert "Do not invent signals" in prompt


def test_unknown_signal_fallback_repairs_toward_allowed_signal_set() -> None:
    repaired = repair_design2sva_candidate(
        task=task(),
        context=context(),
        current_candidate=candidate(),
        metrics=metrics(),
        round_index=1,
        use_llm=False,
    )

    assert "ghost_signal" not in repaired["sva"]
    assert set(repaired["referenced_signals"]) <= {"clk", "rst", "gnt0", "gnt1"}
    assert repaired["repair_metadata"]["changed_by_repair"] is True


def test_design2sva_repair_candidate_schema_accepts_agent_output() -> None:
    schema = json.loads(
        (ROOT / "copilot" / "schemas" / "design2sva_repair_candidate.schema.json").read_text(
            encoding="utf-8"
        )
    )
    repaired = repair_design2sva_candidate(
        task=task(),
        context=context(),
        current_candidate=candidate(),
        metrics=metrics(),
        round_index=1,
        use_llm=False,
    )

    Draft202012Validator(schema).validate(repaired)


def test_rtl_triage_usable_policy_does_not_require_exact_match() -> None:
    row = {
        "valid_json": True,
        "syntax_ok": True,
        "has_hallucinated_signal": False,
        "unsupported_helper_code_issue": False,
        "reset_clock_mismatch": False,
        "exact_match": False,
        "proof_metadata": {
            "proof_status": "proven",
            "vacuity_status": "non_vacuous",
            "syntax_status": "passed",
        },
        "antecedent_metadata": {"extraction_status": "invariant"},
    }

    assert row_sva_usable_for_rtl_triage(row) is True
