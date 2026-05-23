from __future__ import annotations

from pathlib import Path

from copilot.agents.dv_triage_agent import build_prompt, normalize_diagnosis
from copilot.json_utils import extract_json_object
from evaluation.output_quality import hallucinated_signals, source_summary
from tools.build_evidence_packet import build_packet


ROOT = Path(__file__).resolve().parents[1]


def sample_packet() -> dict[str, object]:
    return {
        "case_id": "apb_C6",
        "design_id": "apb_regblock",
        "variant": "correct",
        "task_type": "failure_triage",
        "failing_property": {
            "property_id": "p_read_next_cycle_bad",
            "intent": "Read data should appear one cycle after the access.",
        },
        "signal_role_map": {
            "pclk": "clock",
            "presetn": "reset",
            "psel": "select",
            "penable": "enable",
            "pready": "ready",
            "prdata": "read data",
        },
        "counterexample_summary": {"changed_signals": ["pready", "prdata"]},
    }


def test_extract_json_object_uses_first_valid_object_with_extra_text() -> None:
    text = (
        "```json\n"
        '{"case_id":"apb_C6","predicted_issue_type":"assertion_property_bug"}'
        "\n```\n"
        "Trailing prompt copy with another object: {\"case_id\":\"wrong\"}"
    )

    parsed = extract_json_object(text)

    assert parsed["case_id"] == "apb_C6"
    assert parsed["predicted_issue_type"] == "assertion_property_bug"


def test_triage_prompt_renders_explicit_signal_constraints() -> None:
    prompt = build_prompt(sample_packet())

    assert "ALLOWED_SIGNALS" in prompt
    assert "ASSUMPTION_VACUITY_TRIAGE_HINTS" in prompt
    assert '"pready"' in prompt
    assert "natural-language labels" in prompt
    assert "valid_addr" in prompt
    assert "Return exactly one JSON object" in prompt


def test_normalize_diagnosis_drops_unsupported_suspect_signals() -> None:
    output = {
        "case_id": "apb_C6",
        "predicted_issue_type": "rtl_design_bug",
        "root_cause_ranked": [
            {
                "rank": 1,
                "hypothesis": "The read path timing appears inconsistent.",
                "evidence": ["pready and prdata are visible in the packet."],
            }
        ],
        "suspect_rtl_signals": ["pready", "access", "valid_addr"],
        "suspect_assertions_or_assumptions": [],
        "recommended_next_action": "fix_rtl",
        "debug_checklist": ["Review allowed signals."],
    }

    normalized = normalize_diagnosis(sample_packet(), output)

    assert normalized["source"] == "llm"
    assert normalized["suspect_rtl_signals"] == ["pready"]
    assert hallucinated_signals(normalized, sample_packet()) == []
    assert any("access" in item and "valid_addr" in item for item in normalized["debug_checklist"])


def test_fallback_is_not_counted_as_llm_success() -> None:
    summary = source_summary(
        [
            {
                "system": "structured",
                "source": "structured_fallback",
                "llm_attempted": True,
                "llm_error": "invalid_json",
            }
        ]
    )

    assert summary["llm_success_rate"] == 0.0
    assert summary["fallback_rate"] == 1.0
    assert summary["llm_error_rate"] == 1.0


def test_evidence_packet_marks_blocking_active_assumption_without_gold_label() -> None:
    packet = build_packet(
        ROOT / "benchmarks" / "apb_regblock" / "cases" / "assumption_bug_no_enable_vacuous.json"
    )

    assert "gold_label" not in packet
    vacuity = packet["vacuity_context"]
    assert vacuity["requires_assumption_review"] is True
    assert vacuity["constraint_direction"] == "overconstraint"
    assert vacuity["suspect_assumptions"] == ["a_no_access_phase"]
    assert any(cue["kind"] == "blocking_assumption" for cue in vacuity["assumption_risk_cues"])


def test_evidence_packet_marks_missing_environment_constraint_without_gold_label() -> None:
    packet = build_packet(
        ROOT / "benchmarks" / "fifo_1r1w" / "cases" / "assumption_bug_missing_input_stability.json"
    )

    assert "gold_label" not in packet
    vacuity = packet["vacuity_context"]
    assert vacuity["requires_assumption_review"] is True
    assert vacuity["constraint_direction"] == "underconstraint"
    assert any(cue["kind"] == "missing_environment_constraint" for cue in vacuity["assumption_risk_cues"])


def test_normalize_diagnosis_aligns_issue_with_assumption_vacuity_priority() -> None:
    packet = build_packet(
        ROOT / "benchmarks" / "rv_buffer" / "cases" / "assumption_bug_no_output_stalls.json"
    )
    output = {
        "case_id": "rv_B6",
        "predicted_issue_type": "assertion_property_bug",
        "root_cause_ranked": [
            {
                "rank": 1,
                "hypothesis": "The active assumption removes the stalled-output antecedent.",
                "evidence": ["Active assumptions under suspicion: a_no_output_stalls"],
            }
        ],
        "suspect_rtl_signals": [],
        "suspect_assertions_or_assumptions": ["a_no_output_stalls"],
        "recommended_next_action": "fix_assertion_property",
        "debug_checklist": ["Review the assumption."],
    }

    normalized = normalize_diagnosis(packet, output)

    assert normalized["source"] == "llm"
    assert normalized["predicted_issue_type"] == "assumption_constraint_bug"
    assert normalized["recommended_next_action"] == "fix_assumption_constraint"
    assert any("Aligned issue/action" in item for item in normalized["debug_checklist"])


def test_normalize_diagnosis_does_not_relabel_benign_active_assumption() -> None:
    packet = build_packet(
        ROOT / "benchmarks" / "arbiter_rr2" / "cases" / "assertion_bug_valid_assumption_wrong_mutex.json"
    )
    output = {
        "case_id": "arbiter_A12",
        "predicted_issue_type": "assertion_property_bug",
        "root_cause_ranked": [
            {
                "rank": 1,
                "hypothesis": "The property forbids legal grants.",
                "evidence": ["Reset eventually deasserts; the assertion intent is too broad."],
            }
        ],
        "suspect_rtl_signals": [],
        "suspect_assertions_or_assumptions": ["p_no_grants_bad"],
        "recommended_next_action": "fix_assertion_property",
        "debug_checklist": ["Review assertion intent."],
    }

    normalized = normalize_diagnosis(packet, output)

    assert normalized["predicted_issue_type"] == "assertion_property_bug"
    assert normalized["recommended_next_action"] == "fix_assertion_property"
