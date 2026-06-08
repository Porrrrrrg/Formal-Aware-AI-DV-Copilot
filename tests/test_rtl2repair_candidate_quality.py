from __future__ import annotations

from evaluation.run_rtl2repair_eval import (
    apply_candidate_quality_to_bundle,
    attach_candidate_quality,
    candidate_row,
)


def base_task() -> dict[str, object]:
    return {
        "case_id": "tiny_case",
        "design_id": "tiny_arb",
        "property_id": "p_rtl2repair_01",
        "intent": "Never grant both clients.",
        "visible_signals": ["clk", "rst", "req0", "req1", "gnt0", "gnt1"],
        "clock_reset": {
            "clock": "clk",
            "clock_edge": "posedge",
            "reset": "rst",
            "reset_polarity": "active_high",
        },
        "helper_code_policy": {"allowed": False},
    }


def full_candidate(sva: str, helper_code: str = "") -> dict[str, object]:
    return {
        "property_id": "p_rtl2repair_01",
        "sva": sva,
        "helper_code": helper_code,
        "referenced_signals": [],
        "intent_summary": "Never grant both clients.",
        "source": "unknown",
        "repair_metadata": {
            "round": 0,
            "failure_category": "not_run",
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


def base_bundle(next_owner: str = "unknown") -> dict[str, object]:
    return {
        "root_cause_signals": {
            "clock_reset_mismatch": False,
            "unknown_signals": [],
            "antecedent_reachable": None,
        },
        "repair_recommendation": {
            "next_owner": next_owner,
            "reason": "test",
        },
    }


def test_candidate_quality_detects_hallucinated_helper_and_reset_mismatch() -> None:
    task = base_task()
    context = {"visible_signals": task["visible_signals"]}
    candidate = full_candidate(
        "p_rtl2repair_01: assert property (@(posedge bad_clk) disable iff (rst) ghost |-> gnt1);",
        helper_code="logic seen_ghost;",
    )
    check = attach_candidate_quality(
        task=task,
        context=context,
        candidate=candidate,
        check_result={"syntax_pass": None, "proof_status": None, "vacuity_status": None},
    )
    bundle = base_bundle()
    row = candidate_row(task, context, candidate, check, bundle)
    apply_candidate_quality_to_bundle(row, bundle)

    assert row["valid_json"] is True
    assert row["syntax_ok"] is True
    assert row["has_hallucinated_signal"] is True
    assert set(row["hallucinated_identifiers"]) == {"bad_clk", "ghost"}
    assert row["unsupported_helper_code_issue"] is True
    assert row["reset_clock_mismatch"] is True
    assert row["failure_category"] == "unknown_signal"
    assert bundle["repair_recommendation"]["next_owner"] == "sva"


def test_falsified_reachable_candidate_is_usable_for_rtl_triage() -> None:
    task = base_task()
    context = {"visible_signals": task["visible_signals"]}
    candidate = full_candidate(
        "p_rtl2repair_01: assert property (@(posedge clk) disable iff (rst) !(gnt0 && gnt1));"
    )
    check = attach_candidate_quality(
        task=task,
        context=context,
        candidate=candidate,
        check_result={
            "syntax_pass": True,
            "proof_status": "falsified",
            "vacuity_status": None,
            "antecedent_metadata": {
                "extraction_status": "no_antecedent",
                "has_antecedent": False,
                "requires_antecedent_cover": False,
                "antecedent_reachability": "no_antecedent",
                "cover_status": "not_run",
            },
        },
    )
    row = candidate_row(task, context, candidate, check, base_bundle(next_owner="rtl"))

    assert row["valid_json"] is True
    assert row["has_hallucinated_signal"] is False
    assert row["antecedent_reachable"] is True
    assert row["usable_for_rtl_triage"] is True
